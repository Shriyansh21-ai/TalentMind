"""Resilience policies (Module 8).

The reusable building blocks every runtime call site composes for reliability:
retry with backoff, timeouts, fallbacks, failure classification and a
clock-driven circuit breaker. These are the *single* definitions of each
concept — jobs (Module 1), the execution engine (Module 3) and load management
(Module 7) all reuse them rather than re-implementing.

Everything is deterministic and clock-injected (no wall-clock sleeps, no
randomness), so behaviour is fully testable.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.models import PlatformModel
from src.platform.runtime.common.errors import CircuitOpenError


class BackoffStrategy(str, Enum):
    """How the delay between retry attempts grows."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class FailureCategory(str, Enum):
    """A coarse classification used to decide whether to retry/recover."""

    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class RetryPolicy(PlatformModel):
    """A declarative retry policy with a deterministic backoff schedule."""

    max_attempts: int = 3
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    retry_on: list[FailureCategory] = Field(
        default_factory=lambda: [
            FailureCategory.TRANSIENT,
            FailureCategory.TIMEOUT,
            FailureCategory.RESOURCE,
        ]
    )

    def delay_for(self, attempt: int) -> float:
        """Return the backoff delay (seconds) before ``attempt`` (1-indexed)."""
        n = max(1, attempt)
        if self.strategy == BackoffStrategy.FIXED:
            delay = self.base_delay_seconds
        elif self.strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay_seconds * n
        else:  # EXPONENTIAL
            delay = self.base_delay_seconds * (2 ** (n - 1))
        return min(delay, self.max_delay_seconds)

    def should_retry(self, attempt: int, category: FailureCategory) -> bool:
        """Return whether another attempt is warranted for ``category``."""
        return attempt < self.max_attempts and category in self.retry_on


class TimeoutPolicy(PlatformModel):
    """A wall-clock timeout budget for a single execution."""

    seconds: float = 30.0

    def exceeded(self, elapsed_seconds: float) -> bool:
        """Return whether ``elapsed_seconds`` breaches the budget."""
        return elapsed_seconds > self.seconds


class FallbackPolicy:
    """A fallback invoked when the primary call ultimately fails."""

    def __init__(self, fallback: Callable[[], object]) -> None:
        self._fallback = fallback

    def invoke(self) -> object:
        """Produce the fallback value."""
        return self._fallback()


def classify_failure(exc: BaseException) -> FailureCategory:
    """Classify an exception into a :class:`FailureCategory`.

    Uses the platform error ``code`` where available so classification stays
    consistent with the error hierarchy; unknown exceptions default to
    ``TRANSIENT`` (retryable) which is the safe default for infrastructure.
    """
    code = getattr(exc, "code", "")
    if code in ("task_timeout",):
        return FailureCategory.TIMEOUT
    if code in ("resource_limit_exceeded", "concurrency_limit_exceeded", "queue_overflow"):
        return FailureCategory.RESOURCE
    if code in ("validation_error", "runtime_validation_error", "permission_denied", "not_found"):
        return FailureCategory.PERMANENT
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return FailureCategory.PERMANENT
    return FailureCategory.TRANSIENT


class CircuitState(str, Enum):
    """The three states of a circuit breaker."""

    CLOSED = "closed"  # calls flow normally
    OPEN = "open"  # calls are short-circuited
    HALF_OPEN = "half_open"  # a trial call is allowed


class CircuitBreaker:
    """A clock-driven circuit breaker (Module 7 · Module 8).

    Opens after ``failure_threshold`` consecutive failures; after
    ``recovery_timeout_seconds`` it moves to HALF_OPEN and allows a single trial
    call — a success closes it, a failure re-opens it.
    """

    def __init__(
        self,
        name: str = "circuit",
        *,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        clock: Clock | None = None,
    ) -> None:
        self.name = name
        self._threshold = max(1, failure_threshold)
        self._recovery = recovery_timeout_seconds
        self._clock = clock or SystemClock()
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        """Return the current state, transitioning OPEN→HALF_OPEN if recovered."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = self._clock.now().timestamp() - self._opened_at
            if elapsed >= self._recovery:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow(self) -> bool:
        """Return whether a call may proceed right now."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def guard(self) -> None:
        """Raise :class:`CircuitOpenError` if the circuit is open."""
        if not self.allow():
            raise CircuitOpenError(f"circuit '{self.name}' is open")

    def record_success(self) -> None:
        """Record a success — closes the circuit and resets the counter."""
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        """Record a failure — may trip the circuit to OPEN."""
        self._consecutive_failures += 1
        if self.state == CircuitState.HALF_OPEN:
            self._trip()
        elif self._consecutive_failures >= self._threshold:
            self._trip()

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock.now().timestamp()

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-safe snapshot for dashboards/telemetry."""
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._consecutive_failures,
            "threshold": self._threshold,
        }
