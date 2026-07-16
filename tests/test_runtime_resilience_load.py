"""Modules 7 & 8 tests — resilience framework and load management.

Resilience: retry backoff schedule, failure classification, circuit-breaker
state machine and the composed engine (success / recovered / fallback / failed).
Load: concurrency limits, bulkhead isolation, backpressure and adaptive throttle.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.runtime.common.errors import (
    CircuitOpenError,
    ConcurrencyLimitError,
)
from src.platform.runtime.load import (
    AdaptiveThrottle,
    BackpressureController,
    BackpressureSignal,
    Bulkhead,
    ConcurrencyManager,
    LoadManager,
)
from src.platform.runtime.resilience import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitState,
    FailureCategory,
    FallbackPolicy,
    Outcome,
    RecoveryStrategy,
    ResilienceEngine,
    RetryPolicy,
    classify_failure,
)


# -- resilience policies ----------------------------------------------------


def test_exponential_backoff_schedule():
    policy = RetryPolicy(strategy=BackoffStrategy.EXPONENTIAL, base_delay_seconds=1.0)
    assert [policy.delay_for(n) for n in (1, 2, 3)] == [1.0, 2.0, 4.0]


def test_failure_classification():
    assert classify_failure(ValueError("x")) == FailureCategory.PERMANENT
    assert classify_failure(RuntimeError("x")) == FailureCategory.TRANSIENT


def test_circuit_breaker_trips_and_recovers():
    clock = FrozenClock()
    breaker = CircuitBreaker("db", failure_threshold=2, recovery_timeout_seconds=30, clock=clock)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        breaker.guard()
    clock.advance(seconds=31)
    assert breaker.state == CircuitState.HALF_OPEN
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


# -- resilience engine ------------------------------------------------------


def test_engine_recovers_on_retry():
    engine = ResilienceEngine(clock=FrozenClock())
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    value, report = engine.execute(flaky, retry=RetryPolicy(max_attempts=5))
    assert value == "ok"
    assert report.outcome == Outcome.RECOVERED
    assert report.attempt_count == 3


def test_engine_uses_fallback_when_exhausted():
    engine = ResilienceEngine(clock=FrozenClock())

    def always_fail():
        raise RuntimeError("down")

    value, report = engine.execute(
        always_fail,
        retry=RetryPolicy(max_attempts=1),
        fallback=FallbackPolicy(lambda: "fallback"),
        recovery=RecoveryStrategy.FALLBACK,
    )
    assert value == "fallback"
    assert report.outcome == Outcome.FALLBACK
    assert report.used_fallback


def test_engine_raises_when_no_recovery():
    engine = ResilienceEngine(clock=FrozenClock())

    def permanent():
        raise ValueError("bad input")  # PERMANENT — not retried

    with pytest.raises(ValueError):
        engine.execute(permanent, retry=RetryPolicy(max_attempts=3))


def test_engine_short_circuits_open_breaker():
    clock = FrozenClock()
    engine = ResilienceEngine(clock=clock)
    breaker = CircuitBreaker("x", failure_threshold=1, clock=clock)
    breaker.record_failure()  # opens
    with pytest.raises(CircuitOpenError):
        engine.execute(lambda: 1, circuit=breaker)


# -- load management --------------------------------------------------------


def test_concurrency_manager_limits():
    mgr = ConcurrencyManager(max_concurrent=2)
    mgr.acquire()
    mgr.acquire()
    with pytest.raises(ConcurrencyLimitError):
        mgr.acquire()
    mgr.release()
    assert mgr.try_acquire()


def test_bulkhead_isolates_partitions():
    bulkhead = Bulkhead(default_limit=1)
    bulkhead.acquire("a")
    with pytest.raises(ConcurrencyLimitError):
        bulkhead.acquire("a")
    bulkhead.acquire("b")  # different partition unaffected
    assert bulkhead.snapshot()["b"]["active"] == 1


def test_backpressure_signals():
    controller = BackpressureController(capacity=10, throttle_ratio=0.7)
    assert controller.evaluate(3) == BackpressureSignal.ACCEPT
    assert controller.evaluate(8) == BackpressureSignal.THROTTLE
    assert controller.evaluate(10) == BackpressureSignal.REJECT


def test_adaptive_throttle_aimd():
    throttle = AdaptiveThrottle(initial=10, min_limit=1, max_limit=20)
    throttle.record_success()
    assert throttle.limit == 11
    throttle.record_error()
    assert throttle.limit == 5  # halved


def test_load_manager_admits_and_validates():
    manager = LoadManager(clock=FrozenClock())
    assert manager.admit(0) == BackpressureSignal.ACCEPT
    with pytest.raises(Exception):
        manager.validate_payload(manager.limits.max_payload_bytes + 1)
    assert "circuit" in manager.snapshot()
