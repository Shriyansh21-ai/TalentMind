"""Enterprise event bus (Module 10).

A platform-level publish/subscribe bus with topics, wildcard routing, strict
per-bus ordering, an append-only log for replay, and a dead-letter queue for
handlers that raise. It is synchronous and in-memory, but the surface
(:class:`MessageBroker`) is the seam a future Kafka or RabbitMQ backend binds to
— adapters implement the same ``publish`` / ``subscribe`` / ``replay`` contract.

Routing uses dotted topics (``integration.workday.connected``) matched against
subscriber patterns that may use ``*`` to match a single segment or ``#`` /
``**`` to match the remainder — the conventions AMQP/Kafka users expect.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.integrations.events.models import (
    DeadLetterEntry,
    EnterpriseEvent,
    EventType,
    Subscription,
)

#: An event handler receives the delivered event and returns nothing meaningful.
EventHandler = Callable[[EnterpriseEvent], object]


def topic_matches(pattern: str, topic: str) -> bool:
    """Return whether ``topic`` matches a subscription ``pattern``.

    ``*`` matches exactly one segment; ``#`` or ``**`` (as a trailing token)
    matches one-or-more remaining segments. ``"*"`` alone matches everything.
    """
    if pattern in ("*", "#", "**"):
        return True
    p_parts = pattern.split(".")
    t_parts = topic.split(".")
    for i, p in enumerate(p_parts):
        if p in ("#", "**"):
            return True  # matches the remainder
        if i >= len(t_parts):
            return False
        if p != "*" and p != t_parts[i]:
            return False
    return len(p_parts) == len(t_parts)


@runtime_checkable
class MessageBroker(Protocol):
    """The seam a future Kafka/RabbitMQ backend satisfies."""

    def publish(self, event: EnterpriseEvent) -> EnterpriseEvent: ...
    def subscribe(
        self, topic_pattern: str, handler: EventHandler, *, subscriber: str
    ) -> Subscription: ...
    def replay(
        self, *, topic_pattern: str = "*", from_sequence: int = 0
    ) -> list[EnterpriseEvent]: ...


class EnterpriseEventBus:
    """A synchronous, ordered, replayable in-process event bus."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._sequence = 0
        self._log: list[EnterpriseEvent] = []
        self._subscriptions: list[tuple[Subscription, EventHandler]] = []
        self._dead_letters: list[DeadLetterEntry] = []

    # -- subscribe ----------------------------------------------------------

    def subscribe(
        self, topic_pattern: str, handler: EventHandler, *, subscriber: str = ""
    ) -> Subscription:
        """Register ``handler`` for topics matching ``topic_pattern``."""
        subscription = Subscription(
            id=generate_id("sub"),
            topic_pattern=topic_pattern,
            subscriber=subscriber or getattr(handler, "__name__", "handler"),
        )
        self._subscriptions.append((subscription, handler))
        return subscription

    def unsubscribe(self, subscription_id: str) -> None:
        """Deactivate and remove a subscription."""
        self._subscriptions = [(s, h) for (s, h) in self._subscriptions if s.id != subscription_id]

    def subscriptions(self) -> list[Subscription]:
        """Return the current subscriptions."""
        return [s for (s, _h) in self._subscriptions]

    # -- publish ------------------------------------------------------------

    def publish(
        self,
        topic: str,
        *,
        payload: dict[str, object] | None = None,
        event_type: EventType = EventType.INTEGRATION,
        tenant_id: str | None = None,
        name: str = "",
    ) -> EnterpriseEvent:
        """Assign order, log, and deliver an event to matching subscribers."""
        self._sequence += 1
        now = self._clock.now()
        event = EnterpriseEvent(
            id=generate_id("evt"),
            topic=topic,
            event_type=event_type,
            name=name or topic.split(".")[-1],
            tenant_id=tenant_id,
            sequence=self._sequence,
            payload=payload or {},
            occurred_at=now,
            created_at=now,
            updated_at=now,
        )
        self._log.append(event)
        self._deliver(event)
        return event

    def publish_event(self, event: EnterpriseEvent) -> EnterpriseEvent:
        """Publish a pre-built event (broker-compatible entry point)."""
        return self.publish(
            event.topic,
            payload=event.payload,
            event_type=event.event_type,
            tenant_id=event.tenant_id,
            name=event.name,
        )

    def _deliver(self, event: EnterpriseEvent) -> None:
        for subscription, handler in self._subscriptions:
            if not subscription.active:
                continue
            if not topic_matches(subscription.topic_pattern, event.topic):
                continue
            try:
                handler(event)
            except Exception as exc:  # isolation + dead-letter capture
                self._dead_letters.append(
                    DeadLetterEntry(
                        id=generate_id("dlq"),
                        event=event,
                        subscriber=subscription.subscriber,
                        error=str(exc),
                    )
                )

    # -- replay & history ---------------------------------------------------

    def replay(self, *, topic_pattern: str = "*", from_sequence: int = 0) -> list[EnterpriseEvent]:
        """Return logged events matching ``topic_pattern`` from ``from_sequence``.

        Results are in ascending ``sequence`` order — the same order in which
        they were originally published.
        """
        return [
            e
            for e in self._log
            if e.sequence > from_sequence and topic_matches(topic_pattern, e.topic)
        ]

    def history(self, *, tenant_id: str | None = None) -> list[EnterpriseEvent]:
        """Return the full ordered log, optionally filtered by tenant."""
        if tenant_id is None:
            return list(self._log)
        return [e for e in self._log if e.tenant_id == tenant_id]

    # -- dead letters -------------------------------------------------------

    def dead_letters(self) -> list[DeadLetterEntry]:
        """Return events that failed delivery to at least one subscriber."""
        return list(self._dead_letters)

    def redeliver_dead_letters(self) -> int:
        """Re-attempt delivery of dead-lettered events; return count re-tried.

        Successfully redelivered entries are dropped from the queue; entries that
        fail again are re-queued with an incremented attempt count.
        """
        pending = self._dead_letters
        self._dead_letters = []
        retried = 0
        for entry in pending:
            retried += 1
            delivered = True
            for subscription, handler in self._subscriptions:
                if subscription.subscriber != entry.subscriber:
                    continue
                if not topic_matches(subscription.topic_pattern, entry.event.topic):
                    continue
                try:
                    handler(entry.event)
                except Exception as exc:
                    delivered = False
                    entry.error = str(exc)
                    entry.attempts += 1
            if not delivered:
                self._dead_letters.append(entry)
        return retried
