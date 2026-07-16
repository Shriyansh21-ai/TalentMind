"""Module 4 — Distributed Cache Layer.

A namespaced cache manager over a swappable :class:`CacheProvider`: an in-memory
reference with clock-driven TTL and hit/miss statistics, a Redis placeholder and
a distributed-cache interface. Ships the well-known tenant / session / config /
analytics caches, with tenant-isolated keys. No Redis integration.
"""

from __future__ import annotations

from src.platform.runtime.cache.manager import (
    ANALYTICS,
    CONFIG,
    SESSION,
    TENANT,
    CacheManager,
    CacheNamespace,
    TenantCacheNamespace,
)
from src.platform.runtime.cache.providers import (
    CacheProvider,
    DistributedCacheProvider,
    MemoryCacheProvider,
    RedisCacheProvider,
)

__all__ = [
    "CacheProvider",
    "DistributedCacheProvider",
    "MemoryCacheProvider",
    "RedisCacheProvider",
    "CacheManager",
    "CacheNamespace",
    "TenantCacheNamespace",
    "TENANT",
    "SESSION",
    "CONFIG",
    "ANALYTICS",
]
