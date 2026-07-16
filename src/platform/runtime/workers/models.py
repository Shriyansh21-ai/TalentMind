"""Worker models (Module 2).

The state a worker carries: its lifecycle status, an execution context (scope,
capabilities, concurrency), heartbeat and rolling metrics. Workers are the unit
the pool registers, scales, health-checks and gracefully drains. They are
process-local here, but the shape is chosen so a future distributed worker
(a separate process/pod) maps onto the same record.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import Entity, PlatformModel


class WorkerStatus(str, Enum):
    """The lifecycle state of a worker."""

    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    DRAINING = "draining"  # finishing current work, accepting no new work
    STOPPED = "stopped"
    UNHEALTHY = "unhealthy"

    @property
    def is_available(self) -> bool:
        """Return whether the worker can accept new work."""
        return self in (WorkerStatus.IDLE, WorkerStatus.STARTING)


class WorkerContext(PlatformModel):
    """The execution context a worker runs within."""

    tenant_scope: str | None = None  # None = may process any tenant's work
    capabilities: list[str] = Field(default_factory=list)
    max_concurrency: int = 1


class WorkerMetrics(PlatformModel):
    """Rolling counters for a worker."""

    jobs_processed: int = 0
    jobs_failed: int = 0
    heartbeats: int = 0
    busy_transitions: int = 0

    @property
    def success_rate(self) -> float:
        """Return the fraction of processed jobs that did not fail (0..1)."""
        if self.jobs_processed == 0:
            return 1.0
        return (self.jobs_processed - self.jobs_failed) / self.jobs_processed


class Worker(Entity):
    """A registered worker and its current state."""

    name: str = ""
    status: WorkerStatus = WorkerStatus.STARTING
    context: WorkerContext = Field(default_factory=WorkerContext)
    metrics: WorkerMetrics = Field(default_factory=WorkerMetrics)
    current_job_id: str = ""
    last_heartbeat_at: datetime | None = None
