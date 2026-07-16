"""Resilience engine (Module 8).

Executes a callable through a composed resilience pipeline — circuit breaker →
retry-with-backoff → timeout accounting → fallback → graceful degradation —
and produces a :class:`ResilienceReport` describing what happened. Synchronous
and deterministic: retry "delays" are accumulated (not slept) and timeouts are
measured against the injected clock, so the same code path an async runtime
would take is exercised without real time passing.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.models import PlatformModel
from src.platform.runtime.common.errors import TaskTimeoutError
from src.platform.runtime.resilience.policies import (
    CircuitBreaker,
    FailureCategory,
    FallbackPolicy,
    RetryPolicy,
    TimeoutPolicy,
    classify_failure,
)


class Outcome(str, Enum):
    """The terminal outcome of a resilient execution."""

    SUCCESS = "success"
    RECOVERED = "recovered"  # succeeded on a retry
    FALLBACK = "fallback"  # primary failed, fallback produced a value
    FAILED = "failed"  # exhausted all options


class AttemptRecord(PlatformModel):
    """One attempt inside a resilient execution."""

    attempt: int
    ok: bool
    category: FailureCategory | None = None
    error: str = ""
    backoff_seconds: float = 0.0


class ResilienceReport(PlatformModel):
    """A structured description of a resilient execution."""

    operation: str = ""
    outcome: Outcome = Outcome.SUCCESS
    attempts: list[AttemptRecord] = Field(default_factory=list)
    total_backoff_seconds: float = 0.0
    used_fallback: bool = False
    circuit_state: str = ""

    @property
    def attempt_count(self) -> int:
        """Return how many attempts were made."""
        return len(self.attempts)


class RecoveryStrategy(str, Enum):
    """How the engine behaves when the primary call ultimately fails."""

    RAISE = "raise"  # re-raise the last error
    FALLBACK = "fallback"  # use the fallback policy
    DEGRADE = "degrade"  # return a degraded default without raising


class ResilienceEngine:
    """Compose retry / timeout / circuit-breaker / fallback into one call."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()

    def execute(
        self,
        fn: Callable[[], object],
        *,
        operation: str = "operation",
        retry: RetryPolicy | None = None,
        timeout: TimeoutPolicy | None = None,
        circuit: CircuitBreaker | None = None,
        fallback: FallbackPolicy | None = None,
        recovery: RecoveryStrategy = RecoveryStrategy.RAISE,
        degraded_value: object = None,
    ) -> tuple[object, ResilienceReport]:
        """Run ``fn`` through the resilience pipeline; return (value, report)."""
        policy = retry or RetryPolicy(max_attempts=1)
        report = ResilienceReport(operation=operation)
        last_exc: BaseException | None = None

        attempt = 0
        while True:
            attempt += 1
            if circuit is not None:
                circuit.guard()  # raises CircuitOpenError if open
            start = self._clock.now().timestamp()
            try:
                value = fn()
                elapsed = self._clock.now().timestamp() - start
                if timeout is not None and timeout.exceeded(elapsed):
                    raise TaskTimeoutError(
                        f"{operation} exceeded {timeout.seconds}s (took {elapsed:.3f}s)"
                    )
                report.attempts.append(AttemptRecord(attempt=attempt, ok=True))
                if circuit is not None:
                    circuit.record_success()
                    report.circuit_state = circuit.state.value
                report.outcome = (
                    Outcome.RECOVERED if attempt > 1 else Outcome.SUCCESS
                )
                return value, report
            except BaseException as exc:  # noqa: BLE001 — classify & decide
                last_exc = exc
                category = classify_failure(exc)
                if circuit is not None:
                    circuit.record_failure()
                    report.circuit_state = circuit.state.value
                if policy.should_retry(attempt, category):
                    backoff = policy.delay_for(attempt)
                    report.total_backoff_seconds += backoff
                    report.attempts.append(
                        AttemptRecord(
                            attempt=attempt,
                            ok=False,
                            category=category,
                            error=str(exc),
                            backoff_seconds=backoff,
                        )
                    )
                    continue
                report.attempts.append(
                    AttemptRecord(
                        attempt=attempt, ok=False, category=category, error=str(exc)
                    )
                )
                break

        # Exhausted — apply the recovery strategy.
        if recovery == RecoveryStrategy.FALLBACK and fallback is not None:
            report.outcome = Outcome.FALLBACK
            report.used_fallback = True
            return fallback.invoke(), report
        if recovery == RecoveryStrategy.DEGRADE:
            report.outcome = Outcome.FALLBACK
            report.used_fallback = True
            return degraded_value, report
        report.outcome = Outcome.FAILED
        assert last_exc is not None
        raise last_exc
