"""Worker pool (Module 2).

Manages the fleet of workers: registration, lifecycle transitions, heartbeats,
health (a worker whose heartbeat is stale relative to the injected clock is
marked UNHEALTHY), horizontal scaling (spawn/retire), graceful shutdown
(drain then stop) and aggregate metrics. Deterministic and clock-driven — no
threads or real processes — so the same control surface a future distributed
worker manager exposes is exercised in tests.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.runtime.common.errors import WorkerError
from src.platform.runtime.common.models import HealthState
from src.platform.runtime.events.events import RuntimeEventPublisher
from src.platform.runtime.workers.models import (
    Worker,
    WorkerContext,
    WorkerStatus,
)


class WorkerPool:
    """A registry + lifecycle manager for a fleet of workers."""

    def __init__(
        self,
        *,
        heartbeat_timeout_seconds: float = 60.0,
        events: RuntimeEventPublisher | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._timeout = heartbeat_timeout_seconds
        self._workers: dict[str, Worker] = {}
        self.events = events or RuntimeEventPublisher(clock=self._clock)

    # -- registration & scaling --------------------------------------------

    def register(
        self, *, name: str = "", context: WorkerContext | None = None
    ) -> Worker:
        """Register a new worker in the STARTING state."""
        now = self._clock.now()
        worker = Worker(
            id=generate_id("wrk"),
            name=name or "worker",
            status=WorkerStatus.STARTING,
            context=context or WorkerContext(),
            last_heartbeat_at=now,
            created_at=now,
            updated_at=now,
        )
        self._workers[worker.id] = worker
        self.events.worker("registered", worker_id=worker.id)
        # A freshly registered worker becomes idle (ready) immediately.
        return self._set_status(worker, WorkerStatus.IDLE)

    def deregister(self, worker_id: str) -> None:
        """Remove a worker from the pool."""
        if worker_id in self._workers:
            del self._workers[worker_id]
            self.events.worker("deregistered", worker_id=worker_id)

    def scale_to(self, size: int, *, name_prefix: str = "worker") -> list[Worker]:
        """Scale the *active* fleet to ``size`` (spawn or drain the difference)."""
        if size < 0:
            raise WorkerError("worker pool size cannot be negative")
        active = self.active_workers()
        delta = size - len(active)
        changed: list[Worker] = []
        if delta > 0:
            for i in range(delta):
                changed.append(self.register(name=f"{name_prefix}-{len(active) + i}"))
        elif delta < 0:
            # Retire the most-recently-registered idle workers first.
            for worker in reversed(active[len(active) + delta :]):
                changed.append(self.shutdown(worker.id))
        self.events.worker("scaled", size=size)
        return changed

    # -- lifecycle ----------------------------------------------------------

    def heartbeat(self, worker_id: str) -> Worker:
        """Record a heartbeat, reviving an UNHEALTHY worker back to IDLE."""
        worker = self._require(worker_id)
        worker.last_heartbeat_at = self._clock.now()
        worker.metrics.heartbeats += 1
        if worker.status == WorkerStatus.UNHEALTHY:
            worker.status = WorkerStatus.IDLE
        worker.touch(self._clock.now())
        return worker

    def mark_busy(self, worker_id: str, job_id: str) -> Worker:
        """Transition an available worker to BUSY on ``job_id``."""
        worker = self._require(worker_id)
        if not worker.status.is_available and worker.status != WorkerStatus.BUSY:
            raise WorkerError(
                f"worker '{worker_id}' cannot take work in state {worker.status.value}"
            )
        worker.current_job_id = job_id
        worker.metrics.busy_transitions += 1
        return self._set_status(worker, WorkerStatus.BUSY)

    def mark_idle(self, worker_id: str, *, failed: bool = False) -> Worker:
        """Return a worker to IDLE after finishing (or draining to STOPPED)."""
        worker = self._require(worker_id)
        worker.current_job_id = ""
        worker.metrics.jobs_processed += 1
        if failed:
            worker.metrics.jobs_failed += 1
        if worker.status == WorkerStatus.DRAINING:
            return self._set_status(worker, WorkerStatus.STOPPED)
        return self._set_status(worker, WorkerStatus.IDLE)

    def drain(self, worker_id: str) -> Worker:
        """Begin graceful shutdown: stop accepting work, finish current job."""
        worker = self._require(worker_id)
        if worker.status == WorkerStatus.BUSY:
            return self._set_status(worker, WorkerStatus.DRAINING)
        return self._set_status(worker, WorkerStatus.STOPPED)

    def shutdown(self, worker_id: str) -> Worker:
        """Gracefully drain and stop a worker."""
        worker = self.drain(worker_id)
        self.events.worker("shutdown", worker_id=worker_id)
        return worker

    # -- health -------------------------------------------------------------

    def check_health(self) -> dict[str, HealthState]:
        """Mark workers with stale heartbeats UNHEALTHY; return per-worker state."""
        now = self._clock.now().timestamp()
        result: dict[str, HealthState] = {}
        for worker in self._workers.values():
            if worker.status == WorkerStatus.STOPPED:
                result[worker.id] = HealthState.UNKNOWN
                continue
            last = worker.last_heartbeat_at.timestamp() if worker.last_heartbeat_at else 0
            if now - last > self._timeout:
                worker.status = WorkerStatus.UNHEALTHY
                result[worker.id] = HealthState.UNHEALTHY
            else:
                result[worker.id] = HealthState.HEALTHY
        return result

    def health(self) -> HealthState:
        """Return the aggregate pool health."""
        states = list(self.check_health().values())
        return HealthState.worst([s for s in states if s != HealthState.UNKNOWN])

    # -- queries ------------------------------------------------------------

    def get(self, worker_id: str) -> Worker:
        """Return one worker."""
        return self._require(worker_id)

    def workers(self) -> list[Worker]:
        """Return every worker in the pool."""
        return list(self._workers.values())

    def active_workers(self) -> list[Worker]:
        """Return workers that are not stopped."""
        return [w for w in self._workers.values() if w.status != WorkerStatus.STOPPED]

    def available_worker(self) -> Worker | None:
        """Return the first idle worker able to take new work."""
        for worker in self._workers.values():
            if worker.status.is_available:
                return worker
        return None

    def metrics(self) -> dict[str, int]:
        """Return aggregate fleet metrics."""
        return {
            "total": len(self._workers),
            "active": len(self.active_workers()),
            "busy": sum(1 for w in self._workers.values() if w.status == WorkerStatus.BUSY),
            "idle": sum(1 for w in self._workers.values() if w.status == WorkerStatus.IDLE),
            "unhealthy": sum(
                1 for w in self._workers.values() if w.status == WorkerStatus.UNHEALTHY
            ),
            "jobs_processed": sum(w.metrics.jobs_processed for w in self._workers.values()),
            "jobs_failed": sum(w.metrics.jobs_failed for w in self._workers.values()),
        }

    def _require(self, worker_id: str) -> Worker:
        worker = self._workers.get(worker_id)
        if worker is None:
            raise WorkerError(f"worker '{worker_id}' not registered")
        return worker

    def _set_status(self, worker: Worker, status: WorkerStatus) -> Worker:
        worker.status = status
        worker.touch(self._clock.now())
        return worker
