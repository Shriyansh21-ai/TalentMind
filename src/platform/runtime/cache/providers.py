"""Cache providers (Module 4).

The :class:`CacheProvider` seam plus an in-memory reference and a Redis
placeholder. TTL is clock-driven (no wall-clock sleeps) so expiry is fully
testable, and the in-memory provider tracks hit/miss statistics for the runtime
dashboard. No Redis integration is implemented — :class:`RedisCacheProvider`
signals it is a placeholder until a real client is bound.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.common.clock import Clock, SystemClock
from src.platform.runtime.common.errors import RuntimePlatformError


@runtime_checkable
class CacheProvider(Protocol):
    """A key/value cache backend with optional per-key TTL."""

    name: str

    def get(self, key: str) -> object | None: ...
    def set(self, key: str, value: object, *, ttl_seconds: float | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def clear(self) -> None: ...


@runtime_checkable
class DistributedCacheProvider(CacheProvider, Protocol):
    """A cache shared across processes/nodes (interface only).

    Adds cluster-oriented operations a distributed backend must offer on top of
    the base :class:`CacheProvider` surface.
    """

    def incr(self, key: str, amount: int = 1) -> int: ...
    def keys(self, pattern: str = "*") -> list[str]: ...


class MemoryCacheProvider:
    """A dict-backed, clock-driven TTL cache with hit/miss statistics."""

    def __init__(self, name: str = "memory", *, clock: Clock | None = None) -> None:
        self.name = name
        self._clock = clock or SystemClock()
        # key -> (value, expires_at_epoch | None)
        self._store: dict[str, tuple[object, float | None]] = {}
        self._hits = 0
        self._misses = 0

    def _expired(self, expires_at: float | None) -> bool:
        return expires_at is not None and self._clock.now().timestamp() >= expires_at

    def get(self, key: str) -> object | None:
        """Return the cached value for ``key`` (or ``None`` if absent/expired)."""
        record = self._store.get(key)
        if record is None:
            self._misses += 1
            return None
        value, expires_at = record
        if self._expired(expires_at):
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return value

    def set(self, key: str, value: object, *, ttl_seconds: float | None = None) -> None:
        """Cache ``value`` under ``key`` with an optional TTL."""
        expires_at = (
            self._clock.now().timestamp() + ttl_seconds
            if ttl_seconds is not None
            else None
        )
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Remove ``key`` (no-op if absent)."""
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        """Return whether ``key`` is present and unexpired."""
        return self.get(key) is not None

    def clear(self) -> None:
        """Drop every entry (statistics are retained)."""
        self._store.clear()

    def incr(self, key: str, amount: int = 1) -> int:
        """Atomically (single-threaded) increment an integer counter key."""
        current = self.get(key)
        value = int(current or 0) + amount
        self.set(key, value)
        return value

    def keys(self, pattern: str = "*") -> list[str]:
        """Return live keys, optionally filtered by a simple ``prefix*`` glob."""
        live = [k for k, (_v, exp) in self._store.items() if not self._expired(exp)]
        if pattern in ("", "*"):
            return live
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in live if k.startswith(prefix)]
        return [k for k in live if k == pattern]

    @property
    def stats(self) -> dict[str, int]:
        """Return hit/miss/size statistics for dashboards."""
        return {"hits": self._hits, "misses": self._misses, "size": len(self._store)}

    @property
    def hit_rate(self) -> float:
        """Return the cache hit rate (0..1)."""
        total = self._hits + self._misses
        return self._hits / total if total else 0.0


class RedisCacheProvider:
    """Placeholder for a future Redis-backed distributed cache.

    Present so wiring can target the real seam today; every operation signals it
    is not yet implemented rather than silently succeeding.
    """

    name = "redis"

    def __init__(self, *, url: str = "redis://localhost:6379/0") -> None:
        self.url = url

    def _not_ready(self) -> RuntimePlatformError:
        return RuntimePlatformError(
            "RedisCacheProvider is an architecture placeholder; bind a real "
            "redis client before use",
            code="cache_provider_not_configured",
        )

    def get(self, key: str) -> object | None:
        raise self._not_ready()

    def set(self, key: str, value: object, *, ttl_seconds: float | None = None) -> None:
        raise self._not_ready()

    def delete(self, key: str) -> None:
        raise self._not_ready()

    def exists(self, key: str) -> bool:
        raise self._not_ready()

    def clear(self) -> None:
        raise self._not_ready()

    def incr(self, key: str, amount: int = 1) -> int:
        raise self._not_ready()

    def keys(self, pattern: str = "*") -> list[str]:
        raise self._not_ready()
