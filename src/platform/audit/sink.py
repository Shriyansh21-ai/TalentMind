"""Audit sinks (Module 9).

The :class:`AuditSink` seam lets audit events fan out to additional
destinations (SIEM, cold storage, a webhook) without the service knowing the
detail. Ships an :class:`InMemoryAuditSink` for tests/preview; real exporters
are a future integration.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.audit.models import AuditEvent


@runtime_checkable
class AuditSink(Protocol):
    """A destination that receives every recorded audit event."""

    def emit(self, event: AuditEvent) -> None:
        """Receive an audit event (must not raise on best-effort sinks)."""
        ...


class InMemoryAuditSink:
    """An audit sink that captures events in memory."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        """Append the event to the captured list."""
        self.events.append(event)
