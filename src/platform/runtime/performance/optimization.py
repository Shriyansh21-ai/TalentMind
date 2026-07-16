"""Performance optimization framework (Module 5 · Module 14).

Reusable optimization primitives: thread-safe lazy loading, object pooling, a
connection-pool interface, a cache warmer, a batch (dataloader-style) loader, a
query-optimizer interface, and a :class:`PerformanceProfile` assembled via a
Builder. These are infrastructure building blocks — none touches business logic
— and the stateful ones guard their internals with a lock so they are safe to
share across threads (Module 14 — thread-safe where appropriate).
"""

from __future__ import annotations

import threading
from typing import Callable, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import Field

from src.platform.common.models import PlatformModel

T = TypeVar("T")


class LazyLoader(Generic[T]):
    """Computes a value once, on first access, then memoises it (thread-safe)."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._value: T | None = None
        self._loaded = False
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        """Return whether the value has been computed yet."""
        return self._loaded

    def get(self) -> T:
        """Return the value, computing it on first call (double-checked lock)."""
        if self._loaded:
            return self._value  # type: ignore[return-value]
        with self._lock:
            if not self._loaded:
                self._value = self._factory()
                self._loaded = True
        return self._value  # type: ignore[return-value]

    def reset(self) -> None:
        """Forget the cached value so it is recomputed on next access."""
        with self._lock:
            self._value = None
            self._loaded = False


class ObjectPool(Generic[T]):
    """A bounded pool of reusable objects (reduces allocation churn)."""

    def __init__(
        self,
        factory: Callable[[], T],
        *,
        max_size: int = 16,
        reset: Callable[[T], None] | None = None,
    ) -> None:
        self._factory = factory
        self._max = max(1, max_size)
        self._reset = reset
        self._free: list[T] = []
        self._in_use = 0
        self._created = 0
        self._lock = threading.Lock()

    def acquire(self) -> T:
        """Return a pooled object (reused if available, else newly created)."""
        with self._lock:
            if self._free:
                obj = self._free.pop()
            else:
                obj = self._factory()
                self._created += 1
            self._in_use += 1
            return obj

    def release(self, obj: T) -> None:
        """Return an object to the pool (dropped if the pool is full)."""
        with self._lock:
            self._in_use = max(0, self._in_use - 1)
            if len(self._free) < self._max:
                if self._reset is not None:
                    self._reset(obj)
                self._free.append(obj)

    @property
    def stats(self) -> dict[str, int]:
        """Return pool statistics for the dashboard."""
        return {
            "free": len(self._free),
            "in_use": self._in_use,
            "created": self._created,
            "max_size": self._max,
        }


@runtime_checkable
class ConnectionPool(Protocol):
    """A connection pool seam (interface only — no driver bound)."""

    def acquire(self) -> object: ...
    def release(self, connection: object) -> None: ...
    def size(self) -> int: ...


@runtime_checkable
class QueryOptimizer(Protocol):
    """A query-optimization seam (interface only)."""

    def optimize(self, query: str) -> str: ...


class CacheWarmer:
    """Pre-populates a cache namespace so first requests hit warm data."""

    def __init__(self, namespace) -> None:  # namespace: CacheNamespace-like
        self._namespace = namespace

    def warm(
        self,
        keys: list[str],
        loader: Callable[[str], object],
        *,
        ttl_seconds: float | None = None,
    ) -> int:
        """Load and cache every key; return how many were warmed."""
        warmed = 0
        for key in keys:
            self._namespace.set(key, loader(key), ttl_seconds=ttl_seconds)
            warmed += 1
        return warmed


class BatchLoader(Generic[T]):
    """Collects keys and resolves them in a single batched call (dataloader)."""

    def __init__(self, batch_fn: Callable[[list[str]], dict[str, T]]) -> None:
        self._batch_fn = batch_fn
        self._pending: list[str] = []

    def enqueue(self, key: str) -> None:
        """Queue a key to be resolved on the next :meth:`load`."""
        if key not in self._pending:
            self._pending.append(key)

    def load(self) -> dict[str, T]:
        """Resolve all queued keys in one batched call and clear the queue."""
        if not self._pending:
            return {}
        keys = self._pending
        self._pending = []
        return self._batch_fn(keys)


class PerformanceProfile(PlatformModel):
    """A named bundle of performance settings applied to a workload."""

    name: str = "default"
    batch_size: int = 100
    chunk_size: int = 50
    cache_ttl_seconds: float = 300.0
    pool_size: int = 16
    lazy_loading: bool = True
    cache_warming: bool = False


class PerformanceProfileBuilder:
    """A Builder for :class:`PerformanceProfile` (Module 18 — Builder pattern)."""

    def __init__(self, name: str = "default") -> None:
        self._data: dict[str, object] = {"name": name}

    def with_batch_size(self, size: int) -> "PerformanceProfileBuilder":
        self._data["batch_size"] = size
        return self

    def with_chunk_size(self, size: int) -> "PerformanceProfileBuilder":
        self._data["chunk_size"] = size
        return self

    def with_cache_ttl(self, seconds: float) -> "PerformanceProfileBuilder":
        self._data["cache_ttl_seconds"] = seconds
        return self

    def with_pool_size(self, size: int) -> "PerformanceProfileBuilder":
        self._data["pool_size"] = size
        return self

    def with_lazy_loading(self, enabled: bool) -> "PerformanceProfileBuilder":
        self._data["lazy_loading"] = enabled
        return self

    def with_cache_warming(self, enabled: bool) -> "PerformanceProfileBuilder":
        self._data["cache_warming"] = enabled
        return self

    def build(self) -> PerformanceProfile:
        """Assemble the configured :class:`PerformanceProfile`."""
        return PerformanceProfile(**self._data)
