"""Background job models (Module 1).

The vocabulary of the job platform: a platform-level :class:`JobDefinition`
(blueprint), a tenant-scoped :class:`Job` (an instance with status, priority,
dependencies and retry state), and the supporting status/priority enums and
history records. Jobs are tenant-scoped so the repository and queue isolate one
tenant's work from another's (Module 15 — tenant-safe queues).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum, IntEnum

from pydantic import Field

from src.platform.common.models import Entity, Metadata, TenantScopedEntity
from src.platform.runtime.resilience.policies import RetryPolicy


class JobStatus(str, Enum):
    """The lifecycle state of a job."""

    PENDING = "pending"  # created, not yet queued
    BLOCKED = "blocked"  # waiting on dependencies
    QUEUED = "queued"  # ready to run, in the queue
    SCHEDULED = "scheduled"  # waiting for a future run time
    RUNNING = "running"  # claimed by a worker
    RETRYING = "retrying"  # failed, awaiting another attempt
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Return whether no further transition is possible."""
        return self in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED)


class JobPriority(IntEnum):
    """Job priority — a higher value is dispatched first."""

    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40


class JobHistoryEntry(Entity):
    """A single status transition in a job's history."""

    status: JobStatus
    detail: str = ""


class JobDefinition(Entity):
    """A platform-level blueprint for a kind of job.

    Not tenant-scoped: the same definition is shared by every tenant. The
    ``handler_ref`` is a string key resolved by the registry — jobs never embed
    executable business logic here.
    """

    key: str
    name: str = ""
    description: str = ""
    handler_ref: str = ""
    default_priority: JobPriority = JobPriority.NORMAL
    default_retry: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_seconds: float = 300.0


class Job(TenantScopedEntity):
    """A tenant-scoped job instance."""

    definition_key: str
    name: str = ""
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    payload: dict[str, object] = Field(default_factory=dict)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    attempts: int = 0
    depends_on: list[str] = Field(default_factory=list)
    result: dict[str, object] = Field(default_factory=dict)
    error: str = ""
    scheduled_for: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    history: list[JobHistoryEntry] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)

    @property
    def is_terminal(self) -> bool:
        """Return whether the job has reached a terminal state."""
        return self.status.is_terminal

    def can_retry(self) -> bool:
        """Return whether the retry policy permits another attempt."""
        return self.attempts < self.retry.max_attempts
