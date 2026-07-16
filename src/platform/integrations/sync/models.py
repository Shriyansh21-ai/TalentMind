"""Synchronization framework models (Module 9).

Tenant-scoped records for scheduled/incremental/full sync jobs, the conflicts a
sync detects, and the resolution strategy applied. A :class:`SyncJob` carries an
incremental ``cursor`` so an interrupted sync can be recovered/resumed rather
than restarted.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity


class SyncMode(str, Enum):
    """How much data a sync moves."""

    FULL = "full"
    INCREMENTAL = "incremental"
    SCHEDULED = "scheduled"


class SyncState(str, Enum):
    """Lifecycle of a sync job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"


class ConflictResolution(str, Enum):
    """How a detected conflict is resolved."""

    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    LATEST_WINS = "latest_wins"
    MANUAL = "manual"


class SyncConflict(PlatformModel):
    """A single field-level conflict detected during a sync."""

    entity_id: str
    field: str
    source_value: object = None
    target_value: object = None
    resolution: ConflictResolution = ConflictResolution.MANUAL
    resolved: bool = False
    resolved_value: object = None


class SyncJob(TenantScopedEntity):
    """A tenant-scoped synchronization run and its progress."""

    integration_id: str
    mode: SyncMode = SyncMode.INCREMENTAL
    state: SyncState = SyncState.PENDING
    default_resolution: ConflictResolution = ConflictResolution.SOURCE_WINS
    records_processed: int = 0
    records_failed: int = 0
    conflicts: list[SyncConflict] = Field(default_factory=list)
    cursor: str = ""
    attempts: int = 0
    max_retries: int = 2
    last_error: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def unresolved_conflicts(self) -> int:
        """Return the number of conflicts still awaiting resolution."""
        return sum(1 for c in self.conflicts if not c.resolved)

    @property
    def is_healthy(self) -> bool:
        """Return whether the job completed cleanly with no failures."""
        return (
            self.state == SyncState.COMPLETED
            and self.records_failed == 0
            and self.unresolved_conflicts == 0
        )


class SyncBatch(PlatformModel):
    """The outcome a sync runner reports for one execution of a job."""

    records_processed: int = 0
    records_failed: int = 0
    conflicts: list[SyncConflict] = Field(default_factory=list)
    next_cursor: str = ""
    ok: bool = True
    error: str = ""
