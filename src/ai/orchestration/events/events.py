"""Typed lifecycle events (Module 10).

The orchestrator, workflow engine and delegation layer emit these as work
progresses. Subscribers (the monitor, the telemetry bridge, the UI) consume
them. Events are *facts about the past* ("this happened"); messages on the bus
are *requests/responses between agents*. They are complementary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class EventType(str, Enum):
    """The closed set of orchestration lifecycle events."""

    WORKFLOW_STARTED = "WorkflowStarted"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    WORKFLOW_CANCELLED = "WorkflowCancelled"
    AGENT_STARTED = "AgentStarted"
    AGENT_FINISHED = "AgentFinished"
    TASK_CREATED = "TaskCreated"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"


@dataclass
class OrchestrationEvent:
    """A single lifecycle event.

    Attributes:
        type: The :class:`EventType`.
        workflow_id: The workflow this event belongs to.
        task_id: Related task id (when applicable).
        agent: Related agent name (when applicable).
        message: Human-readable one-liner for logs / the timeline.
        data: Structured extras (latency, error, capability, …).
        timestamp: ISO-8601 creation time (assigned automatically).
    """

    type: EventType
    workflow_id: str = ""
    task_id: Optional[str] = None
    agent: Optional[str] = None
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the event."""
        return {
            "type": self.type.value,
            "workflow_id": self.workflow_id,
            "task_id": self.task_id,
            "agent": self.agent,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }
