"""In-process message bus (Module 5).

A synchronous publish/subscribe hub. Subscribers register a handler against a
:class:`MessageType` (or a free-form topic string, or the wildcard ``"*"``).
Publishing invokes matching handlers in registration order.

Handler exceptions are swallowed and counted — the communication layer must
never let one misbehaving subscriber break a workflow (the same robustness
principle the telemetry logger follows).

The bus keeps a bounded history for the visualization / monitoring layers.
"""

from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Callable, Deque, Dict, List

from src.ai.orchestration.communication.messages import MessageType, SharedMessage

Handler = Callable[[SharedMessage], None]
_WILDCARD = "*"


class MessageBus:
    """Synchronous, thread-safe pub/sub bus with bounded history."""

    def __init__(self, history_size: int = 500) -> None:
        """Create a bus retaining the last ``history_size`` messages."""
        self._subscribers: Dict[str, List[Handler]] = {}
        self._history: Deque[SharedMessage] = deque(maxlen=history_size)
        self._delivery_errors = 0
        self._lock = RLock()

    # -- subscription -------------------------------------------------------

    def subscribe(self, topic, handler: Handler) -> Callable[[], None]:
        """Subscribe ``handler`` to ``topic`` and return an unsubscribe callable.

        Args:
            topic: A :class:`MessageType`, a topic string, or ``"*"`` for all.
            handler: Callable invoked with each matching :class:`SharedMessage`.
        """
        key = topic.value if isinstance(topic, MessageType) else str(topic)
        with self._lock:
            self._subscribers.setdefault(key, []).append(handler)

        def _unsubscribe() -> None:
            with self._lock:
                handlers = self._subscribers.get(key, [])
                if handler in handlers:
                    handlers.remove(handler)

        return _unsubscribe

    # -- publishing ---------------------------------------------------------

    def publish(self, message: SharedMessage) -> None:
        """Deliver ``message`` to every matching subscriber (never raises)."""
        with self._lock:
            self._history.append(message)
            handlers = list(self._subscribers.get(message.routing_topic, []))
            handlers += list(self._subscribers.get(message.type.value, []))
            handlers += list(self._subscribers.get(_WILDCARD, []))

        seen = set()
        for handler in handlers:
            if id(handler) in seen:
                continue
            seen.add(id(handler))
            try:
                handler(message)
            except Exception:  # a bad subscriber must not break the workflow
                with self._lock:
                    self._delivery_errors += 1

    def emit(
        self,
        type: MessageType,
        sender: str,
        payload: dict,
        *,
        recipient=None,
        correlation_id=None,
        topic=None,
    ) -> SharedMessage:
        """Build + publish a :class:`SharedMessage` in one call; return it."""
        message = SharedMessage(
            type=type,
            sender=sender,
            payload=payload,
            recipient=recipient,
            correlation_id=correlation_id,
            topic=topic,
        )
        self.publish(message)
        return message

    # -- introspection ------------------------------------------------------

    def history(self, limit: int = 100) -> List[SharedMessage]:
        """Return the most recent messages (newest last), up to ``limit``."""
        with self._lock:
            return list(self._history)[-limit:]

    @property
    def delivery_errors(self) -> int:
        """Return the count of subscriber handler failures (best-effort)."""
        return self._delivery_errors

    def clear(self) -> None:
        """Drop all history (subscriptions are retained)."""
        with self._lock:
            self._history.clear()
