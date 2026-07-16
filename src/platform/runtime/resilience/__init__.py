"""Module 8 — Resilience Framework.

Retry, fallback, timeout and circuit-breaker policies, deterministic failure
classification, and a :class:`ResilienceEngine` that composes them into one
call with recovery strategies and structured reports. Reused by jobs, the
execution engine and load management.
"""

from __future__ import annotations

from src.platform.runtime.resilience.engine import (
    AttemptRecord,
    Outcome,
    RecoveryStrategy,
    ResilienceEngine,
    ResilienceReport,
)
from src.platform.runtime.resilience.policies import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitState,
    FailureCategory,
    FallbackPolicy,
    RetryPolicy,
    TimeoutPolicy,
    classify_failure,
)

__all__ = [
    "RetryPolicy",
    "BackoffStrategy",
    "TimeoutPolicy",
    "FallbackPolicy",
    "FailureCategory",
    "classify_failure",
    "CircuitBreaker",
    "CircuitState",
    "ResilienceEngine",
    "ResilienceReport",
    "AttemptRecord",
    "Outcome",
    "RecoveryStrategy",
]
