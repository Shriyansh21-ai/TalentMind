"""Event emitter + telemetry bridge (Module 10).

:class:`EventEmitter` is a tiny, robust observer hub for
:class:`OrchestrationEvent`. :class:`TelemetryEventBridge` subscribes to it and
forwards every event into the *existing* platform telemetry sink
(:class:`~src.ai.telemetry.logger.TelemetryLogger`), so orchestration runs show
up alongside agent runs with zero new observability infrastructure — satisfying
"Events should feed telemetry."
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from threading import RLock

from src.ai.orchestration.events.events import EventType, OrchestrationEvent
from src.ai.telemetry.logger import TelemetryLogger, get_default_logger
from src.ai.telemetry.models import TelemetryEvent

Listener = Callable[[OrchestrationEvent], None]
_WILDCARD = "*"


class EventEmitter:
    """Synchronous observer hub for orchestration events (never raises)."""

    def __init__(self, history_size: int = 500) -> None:
        """Create an emitter retaining the last ``history_size`` events."""
        self._listeners: dict[str, list[Listener]] = {}
        self._history: deque[OrchestrationEvent] = deque(maxlen=history_size)
        self._lock = RLock()

    def on(self, event_type, listener: Listener) -> Callable[[], None]:
        """Register ``listener`` for ``event_type`` (or ``"*"``); returns an off()."""
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        with self._lock:
            self._listeners.setdefault(key, []).append(listener)

        def _off() -> None:
            with self._lock:
                listeners = self._listeners.get(key, [])
                if listener in listeners:
                    listeners.remove(listener)

        return _off

    def emit(self, event: OrchestrationEvent) -> OrchestrationEvent:
        """Dispatch ``event`` to matching listeners + wildcard (never raises)."""
        with self._lock:
            self._history.append(event)
            listeners = list(self._listeners.get(event.type.value, []))
            listeners += list(self._listeners.get(_WILDCARD, []))
        for listener in listeners:
            try:
                listener(event)
            except Exception:  # observers must never break the workflow
                pass
        return event

    def history(self, limit: int = 200) -> list[OrchestrationEvent]:
        """Return the most recent events (newest last), up to ``limit``."""
        with self._lock:
            return list(self._history)[-limit:]

    def clear(self) -> None:
        """Drop event history (listeners are retained)."""
        with self._lock:
            self._history.clear()


# Map orchestration events onto the telemetry event's ``status`` field.
_EVENT_STATUS = {
    EventType.WORKFLOW_STARTED: "workflow_started",
    EventType.WORKFLOW_COMPLETED: "workflow_completed",
    EventType.WORKFLOW_CANCELLED: "workflow_cancelled",
    EventType.AGENT_STARTED: "agent_started",
    EventType.AGENT_FINISHED: "agent_finished",
    EventType.TASK_CREATED: "task_created",
    EventType.TASK_COMPLETED: "task_completed",
    EventType.TASK_FAILED: "task_failed",
}


class TelemetryEventBridge:
    """Forwards orchestration events into the platform telemetry log."""

    def __init__(self, telemetry: TelemetryLogger | None = None) -> None:
        """Bind to a telemetry logger (defaults to the shared platform logger)."""
        self.telemetry = telemetry or get_default_logger()

    def attach(self, emitter: EventEmitter) -> Callable[[], None]:
        """Subscribe to every event on ``emitter``; return an unsubscribe callable."""
        return emitter.on(_WILDCARD, self._forward)

    def _forward(self, event: OrchestrationEvent) -> None:
        """Translate one orchestration event into a :class:`TelemetryEvent`."""
        data = event.data or {}
        self.telemetry.record(
            TelemetryEvent(
                request_id=event.workflow_id or "orchestration",
                agent=event.agent or "orchestrator",
                agent_version=str(data.get("agent_version", "orchestration-v1")),
                provider=str(data.get("provider", "orchestration")),
                model=str(data.get("model", "-")),
                status=_EVENT_STATUS.get(event.type, event.type.value),
                latency_ms=float(data.get("latency_ms", 0.0) or 0.0),
                retries=int(data.get("retries", 0) or 0),
                subject_id=event.task_id or event.workflow_id or "global",
                error=data.get("error"),
            )
        )
