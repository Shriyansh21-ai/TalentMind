"""Module 5 — Performance Optimization Framework.

Thread-safe lazy loading, object pooling, connection-pool and query-optimizer
interfaces, a cache warmer, a batch loader, and :class:`PerformanceProfile`
assembled via a Builder. Infrastructure primitives only — no business logic.
"""

from __future__ import annotations

from src.platform.runtime.performance.optimization import (
    BatchLoader,
    CacheWarmer,
    ConnectionPool,
    LazyLoader,
    ObjectPool,
    PerformanceProfile,
    PerformanceProfileBuilder,
    QueryOptimizer,
)

__all__ = [
    "LazyLoader",
    "ObjectPool",
    "ConnectionPool",
    "QueryOptimizer",
    "CacheWarmer",
    "BatchLoader",
    "PerformanceProfile",
    "PerformanceProfileBuilder",
]
