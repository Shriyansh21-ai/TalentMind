"""Module 9 — Synchronization Framework.

Scheduled / incremental / full sync jobs with conflict detection & resolution,
bounded retries, cursor-based recovery and health monitoring. Data movement is
delegated to an injectable runner — no provider is implemented.
"""

from __future__ import annotations

from src.platform.integrations.sync.models import (
    ConflictResolution,
    SyncBatch,
    SyncConflict,
    SyncJob,
    SyncMode,
    SyncState,
)
from src.platform.integrations.sync.service import (
    SyncRunner,
    SynchronizationService,
    detect_conflicts,
    resolve_conflict,
)

__all__ = [
    "SyncMode",
    "SyncState",
    "ConflictResolution",
    "SyncConflict",
    "SyncJob",
    "SyncBatch",
    "SynchronizationService",
    "SyncRunner",
    "detect_conflicts",
    "resolve_conflict",
]
