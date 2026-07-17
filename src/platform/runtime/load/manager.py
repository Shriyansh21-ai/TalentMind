"""Load management (Module 7).

The controls that keep the runtime stable under pressure: a concurrency manager,
bulkhead isolation, rate control, backpressure, adaptive throttling and resource
limits — plus the shared circuit breaker from the resilience module. Composed
into one :class:`LoadManager` façade. Deterministic and clock-driven; the
adaptive/autoscaling hooks compute a *recommended* size without acting, ready
for a future autoscaler to consume.
"""

from __future__ import annotations

from src.platform.api.ratelimit import RateLimiter, RateLimitResult, TokenBucketRateLimiter
from src.platform.common.clock import Clock, SystemClock
from src.platform.runtime.common.errors import ConcurrencyLimitError, ResourceLimitError
from src.platform.runtime.load.models import BackpressureSignal, ResourceLimits
from src.platform.runtime.resilience.policies import CircuitBreaker


class ConcurrencyManager:
    """Bounds the number of concurrently-executing units."""

    def __init__(self, max_concurrent: int = 100) -> None:
        self._max = max(1, max_concurrent)
        self._active = 0

    @property
    def active(self) -> int:
        """Return the number of currently-held slots."""
        return self._active

    @property
    def available(self) -> int:
        """Return the number of free slots."""
        return self._max - self._active

    def acquire(self) -> None:
        """Take a slot, or raise :class:`ConcurrencyLimitError` if full."""
        if self._active >= self._max:
            raise ConcurrencyLimitError(f"concurrency limit reached ({self._max})")
        self._active += 1

    def release(self) -> None:
        """Return a slot (never drops below zero)."""
        self._active = max(0, self._active - 1)

    def try_acquire(self) -> bool:
        """Take a slot if available; return whether it succeeded."""
        try:
            self.acquire()
            return True
        except ConcurrencyLimitError:
            return False


class Bulkhead:
    """Partitioned concurrency isolation — one partition cannot starve another."""

    def __init__(self, *, default_limit: int = 10) -> None:
        self._default = default_limit
        self._partitions: dict[str, ConcurrencyManager] = {}
        self._limits: dict[str, int] = {}

    def configure(self, partition: str, limit: int) -> None:
        """Set the concurrency limit for a named partition."""
        self._limits[partition] = limit
        self._partitions[partition] = ConcurrencyManager(limit)

    def _manager(self, partition: str) -> ConcurrencyManager:
        if partition not in self._partitions:
            self._partitions[partition] = ConcurrencyManager(self._default)
        return self._partitions[partition]

    def acquire(self, partition: str) -> None:
        """Acquire a slot in ``partition`` (isolated from other partitions)."""
        self._manager(partition).acquire()

    def release(self, partition: str) -> None:
        """Release a slot in ``partition``."""
        self._manager(partition).release()

    def snapshot(self) -> dict[str, dict[str, int]]:
        """Return per-partition active/available counts."""
        return {
            name: {"active": mgr.active, "available": mgr.available}
            for name, mgr in self._partitions.items()
        }


class RateControl:
    """A thin wrapper over the platform token-bucket rate limiter."""

    def __init__(self, *, requests_per_minute: int = 600, clock: Clock | None = None) -> None:
        self._limiter: RateLimiter = TokenBucketRateLimiter(
            requests_per_minute=requests_per_minute, clock=clock or SystemClock()
        )

    def check(self, key: str, *, cost: int = 1) -> RateLimitResult:
        """Consume ``cost`` units for ``key`` and report whether allowed."""
        return self._limiter.check(key, cost=cost)

    @property
    def limiter(self) -> RateLimiter:
        """Expose the underlying limiter (e.g. for the execution engine)."""
        return self._limiter


class BackpressureController:
    """Maps a queue's fullness to an accept / throttle / reject decision."""

    def __init__(self, *, capacity: int, throttle_ratio: float = 0.75) -> None:
        self._capacity = max(1, capacity)
        self._throttle_at = int(self._capacity * throttle_ratio)

    def evaluate(self, current_depth: int) -> BackpressureSignal:
        """Return the backpressure decision for ``current_depth``."""
        if current_depth >= self._capacity:
            return BackpressureSignal.REJECT
        if current_depth >= self._throttle_at:
            return BackpressureSignal.THROTTLE
        return BackpressureSignal.ACCEPT


class AdaptiveThrottle:
    """Adjusts a concurrency target based on observed success/error rate.

    Additive-increase / multiplicative-decrease (AIMD): sustained success raises
    the limit toward ``max_limit``; errors halve it toward ``min_limit``.
    """

    def __init__(self, *, initial: int = 10, min_limit: int = 1, max_limit: int = 100) -> None:
        self._limit = initial
        self._min = min_limit
        self._max = max_limit

    @property
    def limit(self) -> int:
        """Return the current recommended concurrency limit."""
        return self._limit

    def record_success(self) -> int:
        """Additively increase the limit (capped at ``max_limit``)."""
        self._limit = min(self._max, self._limit + 1)
        return self._limit

    def record_error(self) -> int:
        """Multiplicatively decrease the limit (floored at ``min_limit``)."""
        self._limit = max(self._min, self._limit // 2)
        return self._limit


class LoadManager:
    """Façade composing every load-management control."""

    def __init__(
        self,
        *,
        limits: ResourceLimits | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.limits = limits or ResourceLimits()
        self.concurrency = ConcurrencyManager(self.limits.max_concurrent_jobs)
        self.bulkhead = Bulkhead()
        self.rate = RateControl(clock=self._clock)
        self.backpressure = BackpressureController(capacity=self.limits.max_queue_depth)
        self.throttle = AdaptiveThrottle()
        self.circuit = CircuitBreaker("runtime", clock=self._clock)

    def validate_payload(self, size_bytes: int) -> None:
        """Enforce the configured max payload size (Module 15)."""
        if size_bytes > self.limits.max_payload_bytes:
            raise ResourceLimitError(
                f"payload {size_bytes}B exceeds limit {self.limits.max_payload_bytes}B"
            )

    def admit(self, current_queue_depth: int) -> BackpressureSignal:
        """Return whether new work should be admitted given queue depth."""
        return self.backpressure.evaluate(current_queue_depth)

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-safe snapshot for the runtime dashboard."""
        return {
            "concurrency": {
                "active": self.concurrency.active,
                "available": self.concurrency.available,
            },
            "adaptive_limit": self.throttle.limit,
            "circuit": self.circuit.snapshot(),
            "bulkheads": self.bulkhead.snapshot(),
        }
