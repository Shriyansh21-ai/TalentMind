"""Typed inter-agent messages (Module 5).

Every cross-agent interaction is a :class:`SharedMessage` on the bus — there is
no direct agent-to-agent method call anywhere in the framework. This is the
seam that keeps agents decoupled: an agent publishes a ``TaskResponse`` and any
number of subscribers (monitor, another agent, the UI) react, without the
producer knowing who they are.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

_counter = itertools.count(1)


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class MessageType(str, Enum):
    """The closed set of message kinds carried by the bus."""

    TASK_REQUEST = "TaskRequest"        # "please run this task"
    TASK_RESPONSE = "TaskResponse"      # "here is the result of a task"
    STATUS_UPDATE = "StatusUpdate"      # progress / heartbeat
    AGENT_EVENT = "AgentEvent"          # lifecycle notification from an agent
    ERROR_EVENT = "ErrorEvent"          # a failure occurred
    COMPLETION_EVENT = "CompletionEvent"  # a workflow/task finished


@dataclass
class SharedMessage:
    """An envelope passed between agents via the :class:`MessageBus`.

    Attributes:
        type: The :class:`MessageType`.
        sender: Name of the producer (agent / orchestrator / monitor).
        payload: Structured, JSON-serializable message body.
        recipient: Target agent name, or ``None`` for a broadcast.
        topic: Optional routing topic (defaults to the message type value).
        correlation_id: Ties a response back to its originating request/workflow.
        id: Monotonic message id (assigned automatically).
        timestamp: ISO-8601 creation time (assigned automatically).
    """

    type: MessageType
    sender: str
    payload: Dict[str, Any] = field(default_factory=dict)
    recipient: Optional[str] = None
    topic: Optional[str] = None
    correlation_id: Optional[str] = None
    id: int = field(default_factory=lambda: next(_counter))
    timestamp: str = field(default_factory=_now_iso)

    @property
    def routing_topic(self) -> str:
        """Return the topic to route on (explicit topic or the type value)."""
        return self.topic or self.type.value

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the message."""
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "topic": self.routing_topic,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
