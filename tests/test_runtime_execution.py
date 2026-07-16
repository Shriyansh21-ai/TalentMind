"""Module 3 tests — task execution engine.

Sequential, parallel, priority, batch, chunk and rate-controlled execution, plus
per-task retry, timeout classification and cooperative cancellation.
"""

from __future__ import annotations

from src.platform.api.ratelimit import TokenBucketRateLimiter
from src.platform.common.clock import FrozenClock
from src.platform.runtime.execution import (
    ExecutionStatus,
    Task,
    TaskContext,
    TaskExecutionEngine,
    TaskPriority,
)
from src.platform.runtime.resilience import RetryPolicy, TimeoutPolicy


def _engine() -> TaskExecutionEngine:
    return TaskExecutionEngine(clock=FrozenClock())


def test_sequential_all_ok():
    engine = _engine()
    report = engine.run_sequential([Task("a", lambda: 1), Task("b", lambda: 2)])
    assert report.all_ok
    assert report.succeeded == 2
    assert [r.value for r in report.results] == [1, 2]


def test_failed_task_is_captured_not_raised():
    engine = _engine()

    def boom():
        raise ValueError("nope")

    report = engine.run_sequential([Task("ok", lambda: 1), Task("bad", boom)])
    assert report.succeeded == 1 and report.failed == 1
    assert report.results[1].status == ExecutionStatus.FAILED


def test_priority_execution_orders_by_priority():
    engine = _engine()
    order: list[str] = []
    tasks = [
        Task("low", lambda: order.append("low"), priority=TaskPriority.LOW),
        Task("crit", lambda: order.append("crit"), priority=TaskPriority.CRITICAL),
        Task("norm", lambda: order.append("norm"), priority=TaskPriority.NORMAL),
    ]
    engine.run_priority(tasks)
    assert order == ["crit", "norm", "low"]


def test_cancellation_skips_remaining():
    engine = _engine()
    ctx = TaskContext()

    def cancel_then():
        ctx.cancel()
        return 1

    report = engine.run_sequential(
        [Task("a", cancel_then), Task("b", lambda: 2)], context=ctx
    )
    assert report.results[0].status == ExecutionStatus.SUCCEEDED
    assert report.results[1].status == ExecutionStatus.CANCELLED


def test_retry_recovers_within_task():
    engine = _engine()
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    report = engine.run_sequential(
        [Task("flaky", flaky, retry=RetryPolicy(max_attempts=3))]
    )
    assert report.results[0].status == ExecutionStatus.SUCCEEDED
    assert report.results[0].attempts == 2


def test_timeout_classified():
    clock = FrozenClock()
    engine = TaskExecutionEngine(clock=clock)

    def slow():
        clock.advance(seconds=10)  # simulate elapsed time
        return "done"

    report = engine.run_sequential(
        [Task("slow", slow, timeout=TimeoutPolicy(seconds=1),
              retry=RetryPolicy(max_attempts=1))]
    )
    assert report.results[0].status == ExecutionStatus.TIMEOUT


def test_batch_and_chunk_processing():
    engine = _engine()
    items = list(range(10))
    batch_report = engine.run_batch(items, lambda x: x * 2, batch_size=4)
    assert len(batch_report.results) == 3  # 4 + 4 + 2
    assert batch_report.all_ok

    chunk_report = engine.run_chunked(items, lambda c: sum(c), chunk_size=5)
    assert len(chunk_report.results) == 2
    assert [r.value for r in chunk_report.results] == [10, 35]


def test_rate_controlled_skips_when_denied():
    clock = FrozenClock()
    engine = TaskExecutionEngine(clock=clock)
    limiter = TokenBucketRateLimiter(requests_per_minute=1, clock=clock)
    tasks = [Task(f"t{i}", lambda: 1) for i in range(3)]
    report = engine.run_rate_controlled(tasks, rate_limiter=limiter, key="k")
    statuses = [r.status for r in report.results]
    assert statuses[0] == ExecutionStatus.SUCCEEDED
    assert ExecutionStatus.SKIPPED in statuses
