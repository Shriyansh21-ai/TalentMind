"""Job scheduler (Module 1).

Holds jobs that are scheduled to run at (or after) a future moment and releases
them when they become due, driven by the injected :class:`Clock`. This is the
framework a future cron/interval provider (Module 11) builds on — no wall-clock
timers are used, so tests advance a :class:`FrozenClock` to make jobs due.
"""

from __future__ import annotations

from datetime import datetime

from src.platform.common.clock import Clock, SystemClock


class JobScheduler:
    """Tracks scheduled job run-times and reports which are due."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        # job_id -> run_at
        self._scheduled: dict[str, datetime] = {}

    def schedule(self, job_id: str, run_at: datetime) -> None:
        """Register ``job_id`` to become due at ``run_at``."""
        self._scheduled[job_id] = run_at

    def cancel(self, job_id: str) -> None:
        """Unschedule a job (no-op if not scheduled)."""
        self._scheduled.pop(job_id, None)

    def due(self, *, now: datetime | None = None) -> list[str]:
        """Return the ids of jobs whose run time has arrived (and drop them)."""
        moment = now or self._clock.now()
        ready = [job_id for job_id, run_at in self._scheduled.items() if run_at <= moment]
        for job_id in ready:
            del self._scheduled[job_id]
        return ready

    def pending(self) -> dict[str, datetime]:
        """Return the currently-scheduled jobs and their run times."""
        return dict(self._scheduled)

    def __len__(self) -> int:
        return len(self._scheduled)
