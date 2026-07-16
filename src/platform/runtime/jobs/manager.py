"""Job manager (Module 1 — the job platform control plane).

Composes the registry, priority queue, scheduler and a tenant-isolated
repository into the single service that governs a job's whole life: submit (with
dependencies and scheduling), claim, complete, fail-with-retry, recover, and
safely cancel. Every transition is tenant-scoped at the repository boundary,
appends to the job's history, records telemetry and emits a runtime event.

No Celery, no threads, no business logic — a deterministic, clock-driven
framework a future distributed executor binds workers to.
"""

from __future__ import annotations

from datetime import datetime

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.runtime.common.errors import JobNotFoundError, RuntimeValidationError
from src.platform.runtime.common.models import Severity
from src.platform.runtime.events.events import RuntimeEventPublisher
from src.platform.runtime.jobs.models import (
    Job,
    JobDefinition,
    JobHistoryEntry,
    JobPriority,
    JobStatus,
)
from src.platform.runtime.jobs.queue import JobQueue
from src.platform.runtime.jobs.registry import JobHandler, JobRegistry
from src.platform.runtime.jobs.scheduler import JobScheduler
from src.platform.runtime.observability.telemetry import RuntimeTelemetry
from src.platform.runtime.resilience.policies import RetryPolicy, classify_failure

_COMPONENT = "jobs"


class JobManager:
    """Submit, dispatch, complete, retry, recover and cancel jobs."""

    def __init__(
        self,
        *,
        registry: JobRegistry | None = None,
        queue: JobQueue | None = None,
        scheduler: JobScheduler | None = None,
        repository: InMemoryRepository[Job] | None = None,
        telemetry: RuntimeTelemetry | None = None,
        events: RuntimeEventPublisher | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.registry = registry or JobRegistry()
        self.queue = queue or JobQueue()
        self.scheduler = scheduler or JobScheduler(clock=self._clock)
        self.repo: InMemoryRepository[Job] = repository or InMemoryRepository("job")
        self.telemetry = telemetry or RuntimeTelemetry(clock=self._clock)
        self.events = events or RuntimeEventPublisher(clock=self._clock)

    # -- definitions --------------------------------------------------------

    def define(
        self, definition: JobDefinition, handler: JobHandler | None = None
    ) -> JobDefinition:
        """Register a job definition (and optional handler)."""
        return self.registry.register(definition, handler)

    # -- submission ---------------------------------------------------------

    def submit(
        self,
        tenant_id: str,
        organization_id: str,
        definition_key: str,
        *,
        payload: dict[str, object] | None = None,
        priority: JobPriority | None = None,
        retry: RetryPolicy | None = None,
        depends_on: list[str] | None = None,
        run_at: datetime | None = None,
    ) -> Job:
        """Create and enqueue (or schedule / block) a job for a tenant."""
        definition = self.registry.get(definition_key)
        deps = depends_on or []
        # Validate every dependency exists within the same tenant scope.
        for dep_id in deps:
            if self.repo.get(dep_id, tenant_id=tenant_id) is None:
                raise RuntimeValidationError(
                    f"dependency job '{dep_id}' not found for tenant"
                )
        now = self._clock.now()
        job = Job(
            id=generate_id("job"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            definition_key=definition_key,
            name=definition.name or definition_key,
            priority=priority or definition.default_priority,
            retry=retry or definition.default_retry,
            payload=payload or {},
            depends_on=deps,
            created_at=now,
            updated_at=now,
        )
        self.repo.add(job)

        if run_at is not None:
            self._transition(job, JobStatus.SCHEDULED, f"scheduled for {run_at.isoformat()}")
            self.scheduler.schedule(job.id, run_at)
        elif self._has_pending_dependencies(job):
            self._transition(job, JobStatus.BLOCKED, "waiting on dependencies")
        else:
            self._enqueue(job)

        self.events.job("submitted", job_id=job.id, tenant_id=tenant_id)
        self.telemetry.log(
            _COMPONENT, "job.submitted", tenant_id=tenant_id,
            message=job.name, fields={"job_id": job.id, "status": job.status.value},
        )
        return job

    # -- dispatch -----------------------------------------------------------

    def promote_scheduled(self, *, now: datetime | None = None) -> list[Job]:
        """Move any due scheduled jobs into the queue (or block on deps)."""
        promoted: list[Job] = []
        for job_id in self.scheduler.due(now=now):
            job = self.repo.get(job_id)
            if job is None or job.status != JobStatus.SCHEDULED:
                continue
            if self._has_pending_dependencies(job):
                self._transition(job, JobStatus.BLOCKED, "waiting on dependencies")
            else:
                self._enqueue(job)
            promoted.append(job)
        return promoted

    def claim(
        self, worker_id: str, *, tenant_id: str | None = None
    ) -> Job | None:
        """Claim the next queued job for a worker (tenant-restricted if given)."""
        job_id = self.queue.dequeue(tenant_id=tenant_id)
        if job_id is None:
            return None
        job = self.repo.require(job_id)
        job.attempts += 1
        job.started_at = self._clock.now()
        job.metadata = job.metadata.set("worker_id", worker_id)
        self._transition(job, JobStatus.RUNNING, f"claimed by {worker_id}")
        self.events.job("started", job_id=job.id, tenant_id=job.tenant_id)
        return job

    def complete(
        self, job_id: str, *, result: dict[str, object] | None = None
    ) -> Job:
        """Mark a running job succeeded and unblock its dependents."""
        job = self.repo.require(job_id)
        job.result = result or {}
        job.finished_at = self._clock.now()
        self._transition(job, JobStatus.SUCCEEDED, "completed")
        self.telemetry.record_execution(f"job:{job.definition_key}", ok=True)
        self.events.job("succeeded", job_id=job.id, tenant_id=job.tenant_id)
        self._unblock_dependents(job.tenant_id)
        return job

    def fail(self, job_id: str, *, error: str = "") -> Job:
        """Fail a running job — retry if the policy allows, else recover/fail."""
        job = self.repo.require(job_id)
        job.error = error
        self.telemetry.record_execution(f"job:{job.definition_key}", ok=False)
        category = classify_failure(
            type("E", (Exception,), {"code": "runtime_error"})()  # transient default
        )
        if job.can_retry() and job.retry.should_retry(job.attempts, category):
            self._transition(job, JobStatus.RETRYING, error or "retrying")
            self._enqueue(job)  # back to QUEUED for another attempt
            self.events.recovery("job_retry", job_id=job.id, tenant_id=job.tenant_id)
            return job
        job.finished_at = self._clock.now()
        self._transition(job, JobStatus.FAILED, error or "failed")
        self.events.failure("job_failed", job_id=job.id, tenant_id=job.tenant_id)
        self.telemetry.log(
            _COMPONENT, "job.failed", severity=Severity.ERROR,
            tenant_id=job.tenant_id, message=error, fields={"job_id": job.id},
        )
        self._fail_blocked_dependents(job)
        return job

    def cancel(self, tenant_id: str, job_id: str) -> Job:
        """Safely cancel a job — never cancels already-completed work."""
        job = self.repo.require(job_id, tenant_id=tenant_id)
        if job.is_terminal:
            return job  # safe: do not flip a finished job
        self.queue.remove(job_id)
        self.scheduler.cancel(job_id)
        job.finished_at = self._clock.now()
        self._transition(job, JobStatus.CANCELLED, "cancelled")
        self.events.job("cancelled", job_id=job.id, tenant_id=tenant_id)
        return job

    # -- queries ------------------------------------------------------------

    def get(self, tenant_id: str, job_id: str) -> Job:
        """Return one job (tenant-isolated)."""
        return self.repo.require(job_id, tenant_id=tenant_id)

    def list(
        self, tenant_id: str, *, status: JobStatus | None = None
    ) -> list[Job]:
        """Return a tenant's jobs, optionally filtered by status."""
        where = None
        if status is not None:
            where = lambda j: j.status == status  # noqa: E731
        return self.repo.list(tenant_id=tenant_id, where=where)

    def history(self, tenant_id: str, job_id: str) -> list[JobHistoryEntry]:
        """Return a job's status-transition history."""
        return list(self.get(tenant_id, job_id).history)

    def stats(self, tenant_id: str) -> dict[str, int]:
        """Return a per-status count of a tenant's jobs."""
        counts: dict[str, int] = {}
        for job in self.list(tenant_id):
            counts[job.status.value] = counts.get(job.status.value, 0) + 1
        return counts

    # -- internals ----------------------------------------------------------

    def _enqueue(self, job: Job) -> None:
        self.queue.enqueue(job)
        self._transition(job, JobStatus.QUEUED, "queued")
        self.events.queue("enqueued", job_id=job.id, tenant_id=job.tenant_id)

    def _transition(self, job: Job, status: JobStatus, detail: str) -> None:
        job.status = status
        now = self._clock.now()
        job.history.append(
            JobHistoryEntry(id=generate_id("jhist"), status=status, detail=detail,
                            created_at=now, updated_at=now)
        )
        job.touch(now)
        self.repo.update(job)

    def _dependencies(self, job: Job) -> list[Job]:
        result: list[Job] = []
        for dep_id in job.depends_on:
            dep = self.repo.get(dep_id, tenant_id=job.tenant_id)
            if dep is not None:
                result.append(dep)
        return result

    def _has_pending_dependencies(self, job: Job) -> bool:
        return any(
            dep.status != JobStatus.SUCCEEDED for dep in self._dependencies(job)
        )

    def _unblock_dependents(self, tenant_id: str) -> None:
        for job in self.list(tenant_id, status=JobStatus.BLOCKED):
            if not self._has_pending_dependencies(job):
                self._enqueue(job)

    def _fail_blocked_dependents(self, failed_job: Job) -> None:
        for job in self.list(failed_job.tenant_id, status=JobStatus.BLOCKED):
            if failed_job.id in job.depends_on:
                job.finished_at = self._clock.now()
                self._transition(
                    job, JobStatus.FAILED, f"dependency {failed_job.id} failed"
                )
                self.events.failure(
                    "dependency_failed", job_id=job.id, tenant_id=job.tenant_id
                )
