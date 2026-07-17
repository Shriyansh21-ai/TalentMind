"""Execution state model + snapshots (Module 12).

Captures *where a workflow is* so it can be observed, and — in a future
milestone — paused, resumed or recovered. The state is a plain, serializable
record maintained by the workflow engine; :meth:`WorkflowState.snapshot` freezes
it into an :class:`ExecutionSnapshot` that could be persisted and rehydrated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.ai.orchestration.models import AgentOutput, TaskStatus


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class WorkflowStatus(str, Enum):
    """Overall status of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # finished but with one or more failed tasks
    FAILED = "failed"  # a required task failed
    CANCELLED = "cancelled"


@dataclass
class TaskState:
    """Mutable execution record for a single task.

    Attributes:
        task_id: The task id.
        capability: The capability requested (for display / recovery).
        status: Current :class:`~src.ai.orchestration.models.TaskStatus`.
        agent: Agent the task was delegated to (once chosen).
        attempts: Number of execution attempts made.
        started_at / finished_at: ISO-8601 timestamps.
        latency_ms: Wall-clock duration of the last attempt.
        output: The task's :class:`AgentOutput` (once produced).
        error: Last error message, if any.
    """

    task_id: str
    capability: str = ""
    status: TaskStatus = TaskStatus.PENDING
    agent: str | None = None
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    latency_ms: float = 0.0
    output: AgentOutput | None = None
    error: str | None = None

    def mark_running(self, agent: str) -> None:
        """Transition to RUNNING and record the delegated agent + start time."""
        self.status = TaskStatus.RUNNING
        self.agent = agent
        self.attempts += 1
        self.started_at = _now_iso()

    def mark_finished(self, output: AgentOutput) -> None:
        """Record a terminal outcome from ``output``."""
        self.output = output
        self.latency_ms = output.latency_ms
        self.finished_at = _now_iso()
        self.status = TaskStatus.COMPLETED if output.ok else TaskStatus.FAILED
        self.error = output.error

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the task state."""
        return {
            "task_id": self.task_id,
            "capability": self.capability,
            "status": self.status.value,
            "agent": self.agent,
            "attempts": self.attempts,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


@dataclass
class AgentState:
    """Aggregate execution record for one agent within a workflow.

    Attributes:
        agent: Agent name.
        invocations: How many tasks it ran.
        failures: How many of those failed.
        total_latency_ms: Summed latency across invocations.
    """

    agent: str
    invocations: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0

    def record(self, output: AgentOutput) -> None:
        """Fold one :class:`AgentOutput` into the aggregate."""
        self.invocations += 1
        self.total_latency_ms += output.latency_ms
        if not output.ok:
            self.failures += 1

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the agent state."""
        return {
            "agent": self.agent,
            "invocations": self.invocations,
            "failures": self.failures,
            "total_latency_ms": round(self.total_latency_ms, 2),
        }


@dataclass
class ExecutionSnapshot:
    """An immutable, serializable freeze of a workflow's progress.

    Enough to (in a future milestone) resume: the set of completed task ids and
    their outputs means an interrupted run can skip finished work.
    """

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    completed_task_ids: list[str]
    pending_task_ids: list[str]
    task_states: dict[str, dict[str, Any]]
    taken_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the snapshot."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "completed_task_ids": list(self.completed_task_ids),
            "pending_task_ids": list(self.pending_task_ids),
            "task_states": self.task_states,
            "taken_at": self.taken_at,
        }


@dataclass
class WorkflowState:
    """Live, mutable state of a workflow run maintained by the engine.

    Attributes:
        workflow_id: Unique run id.
        workflow_name: Name of the executed workflow definition.
        status: Overall :class:`WorkflowStatus`.
        tasks: ``{task_id: TaskState}``.
        agents: ``{agent_name: AgentState}``.
        started_at / finished_at: ISO-8601 timestamps.
    """

    workflow_id: str
    workflow_name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    tasks: dict[str, TaskState] = field(default_factory=dict)
    agents: dict[str, AgentState] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None

    def task(self, task_id: str, capability: str = "") -> TaskState:
        """Return (creating if needed) the :class:`TaskState` for ``task_id``."""
        if task_id not in self.tasks:
            self.tasks[task_id] = TaskState(task_id=task_id, capability=capability)
        return self.tasks[task_id]

    def agent(self, name: str) -> AgentState:
        """Return (creating if needed) the :class:`AgentState` for ``name``."""
        if name not in self.agents:
            self.agents[name] = AgentState(agent=name)
        return self.agents[name]

    def completed_ids(self) -> list[str]:
        """Return ids of tasks that completed successfully."""
        return [t.task_id for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]

    def pending_ids(self) -> list[str]:
        """Return ids of tasks not yet in a terminal state."""
        return [t.task_id for t in self.tasks.values() if not t.status.is_terminal]

    def snapshot(self) -> ExecutionSnapshot:
        """Freeze the current progress into an :class:`ExecutionSnapshot`."""
        return ExecutionSnapshot(
            workflow_id=self.workflow_id,
            workflow_name=self.workflow_name,
            status=self.status,
            completed_task_ids=self.completed_ids(),
            pending_task_ids=self.pending_ids(),
            task_states={tid: ts.to_dict() for tid, ts in self.tasks.items()},
        )
