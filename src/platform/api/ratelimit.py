"""Rate-limit interfaces (Module 10).

The :class:`RateLimiter` seam plus a deterministic token-bucket reference
implementation. The limiter is clock-injected so refill is testable without
real time, and it is keyed per-tenant so one tenant can never exhaust another's
budget.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.models import PlatformModel


class RateLimitResult(PlatformModel):
    """The outcome of a rate-limit check."""

    allowed: bool
    remaining: int
    limit: int


@runtime_checkable
class RateLimiter(Protocol):
    """A per-key request rate limiter."""

    def check(self, key: str, *, cost: int = 1) -> RateLimitResult:
        """Consume ``cost`` units for ``key`` and report whether it was allowed."""
        ...


class TokenBucketRateLimiter:
    """A deterministic token-bucket limiter (requests per minute)."""

    def __init__(
        self, requests_per_minute: int = 120, *, clock: Clock | None = None
    ) -> None:
        self._rate = max(1, requests_per_minute)
        self._clock = clock or SystemClock()
        # key -> (tokens, last_refill_epoch_seconds)
        self._buckets: dict[str, tuple[float, float]] = {}

    def check(self, key: str, *, cost: int = 1) -> RateLimitResult:
        """Refill by elapsed time, then try to consume ``cost`` tokens."""
        now = self._clock.now().timestamp()
        tokens, last = self._buckets.get(key, (float(self._rate), now))
        # Refill: full bucket regenerates over 60 seconds.
        elapsed = max(0.0, now - last)
        tokens = min(float(self._rate), tokens + elapsed * (self._rate / 60.0))
        allowed = tokens >= cost
        if allowed:
            tokens -= cost
        self._buckets[key] = (tokens, now)
        return RateLimitResult(
            allowed=allowed, remaining=int(tokens), limit=self._rate
        )
