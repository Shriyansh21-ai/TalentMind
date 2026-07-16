"""Event bus (Module 12).

A synchronous in-process pub/sub bus that extensions and platform services use
to react to domain events (``organization.created``, ``user.logged_in``, …).
Handlers are isolated: one handler raising never prevents the others from
running, and the error is captured in the returned results.
"""

from __future__ import annotations

from typing import Callable

from src.platform.common.models import PlatformModel

WILDCARD = "*"


class Event(PlatformModel):
    """A named domain event with an arbitrary payload."""

    name: str
    tenant_id: str | None = None
    payload: dict[str, object] = {}


class EventResult(PlatformModel):
    """The outcome of a single handler invocation."""

    handler: str
    ok: bool
    error: str = ""


class EventBus:
    """A synchronous, error-isolating publish/subscribe bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], object]]] = {}

    def subscribe(self, name: str, handler: Callable[[Event], object]) -> None:
        """Subscribe ``handler`` to ``name`` (or ``"*"`` for all events)."""
        self._subscribers.setdefault(name, []).append(handler)

    def publish(self, event: Event) -> list[EventResult]:
        """Deliver ``event`` to matching subscribers; return per-handler results."""
        handlers = [
            *self._subscribers.get(event.name, []),
            *self._subscribers.get(WILDCARD, []),
        ]
        results: list[EventResult] = []
        for handler in handlers:
            label = getattr(handler, "__name__", repr(handler))
            try:
                handler(event)
                results.append(EventResult(handler=label, ok=True))
            except Exception as exc:  # isolation: never let one break the rest
                results.append(EventResult(handler=label, ok=False, error=str(exc)))
        return results
