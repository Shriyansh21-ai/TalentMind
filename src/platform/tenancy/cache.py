"""Tenant-aware cache (Module 2 / Module 14).

A small namespaced cache used to memoise resolved tenant configuration, feature
flags and other hot per-tenant data. Keys are namespaced by ``tenant_id`` so a
cache lookup can never return another tenant's value, and a whole tenant's cache
can be invalidated in one call — important during config changes.
"""

from __future__ import annotations

from typing import Any

from src.platform.tenancy.isolation import TenantIsolationGuard


class TenantCache:
    """A per-tenant namespaced in-memory cache with hit/miss metrics."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._hits = 0
        self._misses = 0

    def get(self, tenant_id: str, key: str) -> Any | None:
        """Return the cached value for ``key`` in ``tenant_id``, or ``None``."""
        full = TenantIsolationGuard.namespaced_key(tenant_id, key)
        if full in self._data:
            self._hits += 1
            return self._data[full]
        self._misses += 1
        return None

    def set(self, tenant_id: str, key: str, value: Any) -> None:
        """Cache ``value`` under ``key`` for ``tenant_id``."""
        self._data[TenantIsolationGuard.namespaced_key(tenant_id, key)] = value

    def get_or_set(self, tenant_id: str, key: str, factory) -> Any:
        """Return the cached value, computing and caching it on a miss."""
        cached = self.get(tenant_id, key)
        if cached is not None:
            return cached
        value = factory()
        self.set(tenant_id, key, value)
        return value

    def invalidate(self, tenant_id: str, key: str | None = None) -> None:
        """Invalidate one key, or the tenant's whole namespace if ``key`` is None."""
        if key is not None:
            self._data.pop(TenantIsolationGuard.namespaced_key(tenant_id, key), None)
            return
        prefix = TenantIsolationGuard.namespaced_key(tenant_id, "")
        for k in [k for k in self._data if k.startswith(prefix)]:
            del self._data[k]

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss counters (for the platform dashboard)."""
        return {"hits": self._hits, "misses": self._misses, "size": len(self._data)}
