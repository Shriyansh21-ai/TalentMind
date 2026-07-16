"""Background services (Module 11).

A framework for recurring maintenance work — scheduled tasks, cleanup (cache,
telemetry), archive/retention and health polling — driven by the injected clock
rather than real timers. A :class:`CronProvider` seam describes the future cron
backend; the in-process :class:`BackgroundServiceManager` runs due tasks when
``tick()`` is called (e.g. by a scheduler thread or the dashboard), so behaviour
is fully deterministic in tests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.models import PlatformModel

#: A background task performs work and returns a JSON-safe summary.
BackgroundTask = Callable[[], dict]


class ScheduledTask(PlatformModel):
    """Bookkeeping for a recurring background task."""

    name: str
    interval_seconds: float
    enabled: bool = True
    run_count: int = 0
    last_run_at: datetime | None = None
    last_result: dict[str, object] = Field(default_factory=dict)


@runtime_checkable
class CronProvider(Protocol):
    """A future cron/interval backend seam (interface only)."""

    def schedule(self, name: str, interval_seconds: float, task: BackgroundTask) -> None: ...
    def unschedule(self, name: str) -> None: ...


class BackgroundServiceManager:
    """Registers recurring maintenance tasks and runs the ones that are due."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._tasks: dict[str, ScheduledTask] = {}
        self._fns: dict[str, BackgroundTask] = {}

    def register(
        self, name: str, interval_seconds: float, task: BackgroundTask
    ) -> ScheduledTask:
        """Register a recurring task."""
        scheduled = ScheduledTask(name=name, interval_seconds=interval_seconds)
        self._tasks[name] = scheduled
        self._fns[name] = task
        return scheduled

    def unregister(self, name: str) -> None:
        """Remove a registered task."""
        self._tasks.pop(name, None)
        self._fns.pop(name, None)

    def _is_due(self, task: ScheduledTask, now: datetime) -> bool:
        if not task.enabled:
            return False
        if task.last_run_at is None:
            return True
        elapsed = now.timestamp() - task.last_run_at.timestamp()
        return elapsed >= task.interval_seconds

    def run(self, name: str) -> dict:
        """Run a single task now, updating its bookkeeping."""
        task = self._tasks[name]
        result = self._fns[name]()
        task.run_count += 1
        task.last_run_at = self._clock.now()
        task.last_result = result
        return result

    def tick(self, *, now: datetime | None = None) -> dict[str, dict]:
        """Run every due task; return the results keyed by task name."""
        moment = now or self._clock.now()
        results: dict[str, dict] = {}
        for name, task in self._tasks.items():
            if self._is_due(task, moment):
                results[name] = self.run(name)
        return results

    def tasks(self) -> list[ScheduledTask]:
        """Return the registered tasks and their state."""
        return list(self._tasks.values())


# -- ready-made maintenance task factories ---------------------------------


def cache_cleanup_task(cache_manager) -> BackgroundTask:
    """Return a task that reports cache stats (expiry is lazy/on-read)."""

    def _task() -> dict:
        stats = cache_manager.stats()
        return {"action": "cache_cleanup", **stats}

    return _task


def telemetry_cleanup_task(telemetry, *, keep: int = 200) -> BackgroundTask:
    """Return a task that trims the runtime telemetry log ring."""

    def _task() -> dict:
        before = len(telemetry.logs(limit=10_000))
        telemetry._logs = telemetry._logs[-keep:]  # bounded retention
        after = len(telemetry.logs(limit=10_000))
        return {"action": "telemetry_cleanup", "removed": before - after, "kept": after}

    return _task


def retention_task(repository, *, keep_terminal: bool = True) -> BackgroundTask:
    """Return a task that reports retention candidates (archival is external)."""

    def _task() -> dict:
        total = repository.count()
        return {"action": "retention", "total_records": total}

    return _task


def health_polling_task(aggregator) -> BackgroundTask:
    """Return a task that polls the health aggregator and reports overall state."""

    def _task() -> dict:
        report = aggregator.check()
        return {"action": "health_poll", "state": report.state.value}

    return _task
