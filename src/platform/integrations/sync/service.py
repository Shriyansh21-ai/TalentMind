"""Synchronization service (Module 9).

Schedules and runs sync jobs (full / incremental / scheduled), detects and
resolves conflicts, retries transient failures and recovers interrupted runs
from their cursor. The actual data movement is delegated to an injectable
``SyncRunner`` — no provider is implemented here, so the default runner is a
deterministic no-op and tests inject runners that succeed, fail or conflict.
"""

from __future__ import annotations

from collections.abc import Callable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.integrations.sync.models import (
    ConflictResolution,
    SyncBatch,
    SyncConflict,
    SyncJob,
    SyncMode,
    SyncState,
)

#: A runner performs one execution of a job and reports a :class:`SyncBatch`.
SyncRunner = Callable[[SyncJob], SyncBatch]


def _noop_runner(job: SyncJob) -> SyncBatch:
    """Default offline runner — completes immediately with nothing to do."""
    return SyncBatch(ok=True, next_cursor=job.cursor)


def detect_conflicts(
    entity_id: str,
    source: dict[str, object],
    target: dict[str, object],
    *,
    fields: list[str] | None = None,
) -> list[SyncConflict]:
    """Return field-level conflicts where ``source`` and ``target`` differ."""
    keys = fields if fields is not None else sorted(set(source) & set(target))
    conflicts: list[SyncConflict] = []
    for field in keys:
        if source.get(field) != target.get(field):
            conflicts.append(
                SyncConflict(
                    entity_id=entity_id,
                    field=field,
                    source_value=source.get(field),
                    target_value=target.get(field),
                )
            )
    return conflicts


def resolve_conflict(
    conflict: SyncConflict,
    strategy: ConflictResolution,
    *,
    source_newer: bool = True,
) -> SyncConflict:
    """Resolve ``conflict`` using ``strategy`` (MANUAL is left unresolved)."""
    if strategy == ConflictResolution.SOURCE_WINS:
        conflict.resolved_value = conflict.source_value
        conflict.resolved = True
    elif strategy == ConflictResolution.TARGET_WINS:
        conflict.resolved_value = conflict.target_value
        conflict.resolved = True
    elif strategy == ConflictResolution.LATEST_WINS:
        conflict.resolved_value = conflict.source_value if source_newer else conflict.target_value
        conflict.resolved = True
    conflict.resolution = strategy
    return conflict


class SynchronizationService:
    """Manage the lifecycle, conflicts and recovery of sync jobs."""

    def __init__(
        self,
        *,
        runner: SyncRunner | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._runner = runner or _noop_runner
        self.jobs_repo: InMemoryRepository[SyncJob] = InMemoryRepository("sync_job")

    # -- scheduling ---------------------------------------------------------

    def schedule(
        self,
        tenant_id: str,
        organization_id: str,
        integration_id: str,
        *,
        mode: SyncMode = SyncMode.INCREMENTAL,
        default_resolution: ConflictResolution = ConflictResolution.SOURCE_WINS,
        max_retries: int = 2,
        cursor: str = "",
    ) -> SyncJob:
        """Create a PENDING sync job for an integration."""
        now = self._clock.now()
        job = SyncJob(
            id=generate_id("sync"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            integration_id=integration_id,
            mode=mode,
            default_resolution=default_resolution,
            max_retries=max_retries,
            cursor=cursor,
            created_at=now,
            updated_at=now,
        )
        return self.jobs_repo.add(job)

    # -- execution ----------------------------------------------------------

    def run(self, tenant_id: str, job_id: str) -> SyncJob:
        """Execute a job with bounded retries, resolving conflicts by policy."""
        job = self.jobs_repo.require(job_id, tenant_id=tenant_id)
        job.state = SyncState.RUNNING
        job.started_at = self._clock.now()

        batch: SyncBatch | None = None
        while job.attempts <= job.max_retries:
            job.attempts += 1
            try:
                batch = self._runner(job)
            except Exception as exc:  # transient failure → retry
                job.last_error = str(exc)
                batch = SyncBatch(ok=False, error=str(exc))
            if batch.ok:
                break

        assert batch is not None
        self._apply_batch(job, batch)
        job.finished_at = self._clock.now()
        job.touch(job.finished_at)
        return self.jobs_repo.update(job)

    def _apply_batch(self, job: SyncJob, batch: SyncBatch) -> None:
        job.records_processed += batch.records_processed
        job.records_failed += batch.records_failed
        for conflict in batch.conflicts:
            if conflict.resolution == ConflictResolution.MANUAL and not conflict.resolved:
                resolve_conflict(conflict, job.default_resolution)
            job.conflicts.append(conflict)
        if batch.next_cursor:
            job.cursor = batch.next_cursor
        if batch.ok:
            job.state = SyncState.COMPLETED
            job.last_error = ""
        else:
            job.state = SyncState.FAILED
            job.last_error = batch.error or job.last_error

    def recover(self, tenant_id: str, job_id: str) -> SyncJob:
        """Resume a FAILED job from its cursor (incremental recovery)."""
        job = self.jobs_repo.require(job_id, tenant_id=tenant_id)
        if job.state != SyncState.FAILED:
            return job
        job.state = SyncState.RECOVERING
        job.attempts = 0  # fresh retry budget for the recovery pass
        self.jobs_repo.update(job)
        return self.run(tenant_id, job_id)

    def resolve(
        self,
        tenant_id: str,
        job_id: str,
        entity_id: str,
        field: str,
        strategy: ConflictResolution,
    ) -> SyncJob:
        """Manually resolve a specific conflict on a job."""
        job = self.jobs_repo.require(job_id, tenant_id=tenant_id)
        for conflict in job.conflicts:
            if conflict.entity_id == entity_id and conflict.field == field:
                resolve_conflict(conflict, strategy)
        job.touch(self._clock.now())
        return self.jobs_repo.update(job)

    # -- status & health ----------------------------------------------------

    def jobs(self, tenant_id: str, *, integration_id: str | None = None) -> list[SyncJob]:
        """Return a tenant's sync jobs, optionally for one integration."""
        where = None
        if integration_id is not None:
            where = lambda j: j.integration_id == integration_id  # noqa: E731
        return self.jobs_repo.list(tenant_id=tenant_id, where=where)

    def health(self, tenant_id: str, integration_id: str) -> dict[str, object]:
        """Return a small health summary for an integration's sync history."""
        jobs = self.jobs(tenant_id, integration_id=integration_id)
        completed = [j for j in jobs if j.state == SyncState.COMPLETED]
        failed = [j for j in jobs if j.state == SyncState.FAILED]
        return {
            "total_jobs": len(jobs),
            "completed": len(completed),
            "failed": len(failed),
            "records_processed": sum(j.records_processed for j in jobs),
            "unresolved_conflicts": sum(j.unresolved_conflicts for j in jobs),
            "healthy": len(failed) == 0 and all(j.unresolved_conflicts == 0 for j in jobs),
        }
