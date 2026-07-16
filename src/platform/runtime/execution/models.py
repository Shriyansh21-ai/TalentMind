"""Task execution models (Module 3).

A :class:`Task` (a named callable plus its per-task resilience knobs), the
:class:`TaskContext` threaded through an execution (correlation id, tenant,
cooperative cancellation), and the :class:`TaskResult` / :class:`ExecutionReport`
value objects returned by the engine.

:class:`Task` is a plain class (not pydantic) because it holds a callable; the
results and reports are pydantic so they are JSON-safe for the dashboard.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Callable

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.runtime.resilience.policies import RetryPolicy, TimeoutPolicy


class TaskPriority(IntEnum):
    """Task priority — a higher value runs first in priority execution."""

    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40


class ExecutionStatus(str, Enum):
    """The outcome of a single task."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"  # e.g. throttled by rate control


class Task:
    """A named unit of work: a callable plus its resilience configuration."""

    def __init__(
        self,
        name: str,
        fn: Callable[[], object],
        *,
        priority: TaskPriority = TaskPriority.NORMAL,
        retry: RetryPolicy | None = None,
        timeout: TimeoutPolicy | None = None,
    ) -> None:
        self.name = name
        self.fn = fn
        self.priority = priority
        self.retry = retry
        self.timeout = timeout


class TaskContext(PlatformModel):
    """Context threaded through an execution (supports cooperative cancel)."""

    correlation_id: str = ""
    tenant_id: str | None = None
    cancelled: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)

    def cancel(self) -> None:
        """Request cancellation of the remaining tasks in the execution."""
        self.cancelled = True


class TaskResult(PlatformModel):
    """The result of executing a single task."""

    name: str
    status: ExecutionStatus
    value: object = None
    error: str = ""
    attempts: int = 0
    duration_ms: float = 0.0

    @property
    def ok(self) -> bool:
        """Return whether the task succeeded."""
        return self.status == ExecutionStatus.SUCCEEDED


class ExecutionReport(PlatformModel):
    """A structured summary of a batch/sequence/parallel execution."""

    mode: str = ""
    results: list[TaskResult] = Field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def succeeded(self) -> int:
        """Return the number of successful tasks."""
        return sum(1 for r in self.results if r.status == ExecutionStatus.SUCCEEDED)

    @property
    def failed(self) -> int:
        """Return the number of failed/timed-out tasks."""
        return sum(
            1
            for r in self.results
            if r.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)
        )

    @property
    def cancelled(self) -> int:
        """Return the number of cancelled tasks."""
        return sum(1 for r in self.results if r.status == ExecutionStatus.CANCELLED)

    @property
    def all_ok(self) -> bool:
        """Return whether every task succeeded."""
        return self.failed == 0 and self.cancelled == 0 and bool(self.results)
