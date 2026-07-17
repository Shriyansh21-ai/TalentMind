"""Task execution engine (Module 3).

Executes tasks under a range of strategies — sequential, parallel, batch, chunk,
priority-ordered and rate-controlled — each task run through the shared
:class:`ResilienceEngine` (retry + timeout) and honouring cooperative
cancellation via the :class:`TaskContext`. Execution is deterministic: "parallel"
runs collect independent results without ordering guarantees between tasks, the
same contract a real thread/async pool would provide, but without real
concurrency so tests stay reproducible.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from src.platform.api.ratelimit import RateLimiter
from src.platform.common.clock import Clock, SystemClock
from src.platform.runtime.execution.models import (
    ExecutionReport,
    ExecutionStatus,
    Task,
    TaskContext,
    TaskResult,
)
from src.platform.runtime.observability.telemetry import RuntimeTelemetry
from src.platform.runtime.resilience.engine import ResilienceEngine
from src.platform.runtime.resilience.policies import RetryPolicy, TimeoutPolicy

_COMPONENT = "execution"


class TaskExecutionEngine:
    """Runs tasks under sequential / parallel / batch / chunk / rate strategies."""

    def __init__(
        self,
        *,
        resilience: ResilienceEngine | None = None,
        telemetry: RuntimeTelemetry | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._resilience = resilience or ResilienceEngine(clock=self._clock)
        self.telemetry = telemetry or RuntimeTelemetry(clock=self._clock)

    # -- single task --------------------------------------------------------

    def _run_task(self, task: Task, context: TaskContext) -> TaskResult:
        """Execute one task through the resilience pipeline."""
        if context.cancelled:
            return TaskResult(name=task.name, status=ExecutionStatus.CANCELLED)
        start = self._clock.now().timestamp()
        retry = task.retry or RetryPolicy(max_attempts=1)
        timeout: TimeoutPolicy | None = task.timeout
        try:
            value, report = self._resilience.execute(
                task.fn, operation=task.name, retry=retry, timeout=timeout
            )
            duration = (self._clock.now().timestamp() - start) * 1000.0
            self.telemetry.record_latency(f"task:{task.name}", duration)
            self.telemetry.record_execution(f"task:{task.name}", ok=True)
            return TaskResult(
                name=task.name,
                status=ExecutionStatus.SUCCEEDED,
                value=value,
                attempts=report.attempt_count,
                duration_ms=duration,
            )
        except Exception as exc:  # noqa: BLE001 — surface as a failed result
            duration = (self._clock.now().timestamp() - start) * 1000.0
            self.telemetry.record_execution(f"task:{task.name}", ok=False)
            status = (
                ExecutionStatus.TIMEOUT
                if getattr(exc, "code", "") == "task_timeout"
                else ExecutionStatus.FAILED
            )
            return TaskResult(name=task.name, status=status, error=str(exc), duration_ms=duration)

    # -- strategies ---------------------------------------------------------

    def run_sequential(
        self, tasks: list[Task], *, context: TaskContext | None = None
    ) -> ExecutionReport:
        """Run tasks one after another, stopping remaining on cancellation."""
        ctx = context or TaskContext()
        report = ExecutionReport(mode="sequential")
        start = self._clock.now().timestamp()
        for task in tasks:
            report.results.append(self._run_task(task, ctx))
        report.total_duration_ms = (self._clock.now().timestamp() - start) * 1000.0
        return report

    def run_parallel(
        self, tasks: list[Task], *, context: TaskContext | None = None
    ) -> ExecutionReport:
        """Run independent tasks (no ordering guarantee between them)."""
        ctx = context or TaskContext()
        report = ExecutionReport(mode="parallel")
        start = self._clock.now().timestamp()
        for task in tasks:  # deterministic stand-in for a real pool
            report.results.append(self._run_task(task, ctx))
        report.total_duration_ms = (self._clock.now().timestamp() - start) * 1000.0
        return report

    def run_priority(
        self, tasks: list[Task], *, context: TaskContext | None = None
    ) -> ExecutionReport:
        """Run tasks highest-priority first."""
        ordered = sorted(tasks, key=lambda t: int(t.priority), reverse=True)
        report = self.run_sequential(ordered, context=context)
        report.mode = "priority"
        return report

    def run_batch(
        self,
        items: Iterable[object],
        fn: Callable[[object], object],
        *,
        batch_size: int = 100,
        context: TaskContext | None = None,
    ) -> ExecutionReport:
        """Process ``items`` in batches of ``batch_size`` (one task per batch)."""
        ctx = context or TaskContext()
        materialized = list(items)
        report = ExecutionReport(mode="batch")
        start = self._clock.now().timestamp()
        for offset in range(0, len(materialized), max(1, batch_size)):
            batch = materialized[offset : offset + batch_size]
            task = Task(
                name=f"batch[{offset}:{offset + len(batch)}]",
                fn=lambda b=batch: [fn(item) for item in b],
            )
            report.results.append(self._run_task(task, ctx))
        report.total_duration_ms = (self._clock.now().timestamp() - start) * 1000.0
        return report

    def run_chunked(
        self,
        items: Iterable[object],
        fn: Callable[[list], object],
        *,
        chunk_size: int = 50,
        context: TaskContext | None = None,
    ) -> ExecutionReport:
        """Process ``items`` in chunks, handing each whole chunk to ``fn``."""
        ctx = context or TaskContext()
        materialized = list(items)
        report = ExecutionReport(mode="chunked")
        start = self._clock.now().timestamp()
        for offset in range(0, len(materialized), max(1, chunk_size)):
            chunk = materialized[offset : offset + chunk_size]
            task = Task(name=f"chunk[{offset}]", fn=lambda c=chunk: fn(c))
            report.results.append(self._run_task(task, ctx))
        report.total_duration_ms = (self._clock.now().timestamp() - start) * 1000.0
        return report

    def run_rate_controlled(
        self,
        tasks: list[Task],
        *,
        rate_limiter: RateLimiter,
        key: str = "execution",
        context: TaskContext | None = None,
    ) -> ExecutionReport:
        """Run tasks, skipping any that the rate limiter denies (throttled)."""
        ctx = context or TaskContext()
        report = ExecutionReport(mode="rate_controlled")
        start = self._clock.now().timestamp()
        for task in tasks:
            if not rate_limiter.check(key).allowed:
                report.results.append(
                    TaskResult(
                        name=task.name,
                        status=ExecutionStatus.SKIPPED,
                        error="rate limited",
                    )
                )
                continue
            report.results.append(self._run_task(task, ctx))
        report.total_duration_ms = (self._clock.now().timestamp() - start) * 1000.0
        return report
