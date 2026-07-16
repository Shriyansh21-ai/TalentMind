"""Cache manager (Module 4).

Organises the cache surface into **namespaces** over a swappable
:class:`CacheProvider`, and exposes the well-known runtime caches (tenant,
session, configuration, analytics). Every namespace prefixes its keys so
namespaces never collide, and the tenant cache additionally namespaces by tenant
via :class:`~src.platform.tenancy.isolation.TenantIsolationGuard` so one tenant
can never read another's cached value (Module 15 — tenant-safe).
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.runtime.cache.providers import CacheProvider, MemoryCacheProvider
from src.platform.tenancy.isolation import TenantIsolationGuard

# Well-known namespaces (Module 4 requires tenant/session/config/analytics).
TENANT = "tenant"
SESSION = "session"
CONFIG = "config"
ANALYTICS = "analytics"


class CacheNamespace:
    """A key-prefixed view over a shared provider."""

    def __init__(self, provider: CacheProvider, namespace: str) -> None:
        self._provider = provider
        self._namespace = namespace

    def _key(self, key: str) -> str:
        return f"ns:{self._namespace}:{key}"

    def get(self, key: str) -> object | None:
        """Return a namespaced value (or ``None``)."""
        return self._provider.get(self._key(key))

    def set(self, key: str, value: object, *, ttl_seconds: float | None = None) -> None:
        """Cache a namespaced value with an optional TTL."""
        self._provider.set(self._key(key), value, ttl_seconds=ttl_seconds)

    def delete(self, key: str) -> None:
        """Invalidate a single namespaced key."""
        self._provider.delete(self._key(key))

    def exists(self, key: str) -> bool:
        """Return whether a namespaced key is present."""
        return self._provider.exists(self._key(key))

    def get_or_set(
        self, key: str, factory, *, ttl_seconds: float | None = None
    ) -> object:
        """Return the cached value, computing and caching it on a miss."""
        found = self.get(key)
        if found is not None:
            return found
        value = factory()
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


class TenantCacheNamespace(CacheNamespace):
    """A namespace whose keys are additionally isolated per tenant."""

    def _tenant_key(self, tenant_id: str, key: str) -> str:
        return TenantIsolationGuard.namespaced_key(tenant_id, key)

    def get_for(self, tenant_id: str, key: str) -> object | None:
        """Return a tenant-scoped cached value."""
        return self.get(self._tenant_key(tenant_id, key))

    def set_for(
        self, tenant_id: str, key: str, value: object, *, ttl_seconds: float | None = None
    ) -> None:
        """Cache a tenant-scoped value."""
        self.set(self._tenant_key(tenant_id, key), value, ttl_seconds=ttl_seconds)

    def invalidate_for(self, tenant_id: str, key: str) -> None:
        """Invalidate a tenant-scoped key."""
        self.delete(self._tenant_key(tenant_id, key))


class CacheManager:
    """Manages namespaced caches over a single swappable provider."""

    def __init__(
        self,
        provider: CacheProvider | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.provider: CacheProvider = provider or MemoryCacheProvider(clock=self._clock)
        self._namespaces: dict[str, CacheNamespace] = {}

    def namespace(self, name: str) -> CacheNamespace:
        """Return (creating on first use) a plain namespace."""
        if name not in self._namespaces:
            self._namespaces[name] = CacheNamespace(self.provider, name)
        return self._namespaces[name]

    def tenant_namespace(self, name: str = TENANT) -> TenantCacheNamespace:
        """Return (creating on first use) a tenant-isolated namespace."""
        existing = self._namespaces.get(name)
        if not isinstance(existing, TenantCacheNamespace):
            existing = TenantCacheNamespace(self.provider, name)
            self._namespaces[name] = existing
        return existing

    # -- well-known caches --------------------------------------------------

    @property
    def tenant_cache(self) -> TenantCacheNamespace:
        """The per-tenant cache (tenant-isolated keys)."""
        return self.tenant_namespace(TENANT)

    @property
    def session_cache(self) -> CacheNamespace:
        """The session cache."""
        return self.namespace(SESSION)

    @property
    def config_cache(self) -> CacheNamespace:
        """The configuration cache."""
        return self.namespace(CONFIG)

    @property
    def analytics_cache(self) -> CacheNamespace:
        """The analytics cache."""
        return self.namespace(ANALYTICS)

    # -- invalidation & stats ----------------------------------------------

    def invalidate_all(self) -> None:
        """Clear the entire underlying provider (every namespace)."""
        self.provider.clear()

    def stats(self) -> dict[str, object]:
        """Return provider statistics (when the provider exposes them)."""
        stats = getattr(self.provider, "stats", None)
        return dict(stats) if isinstance(stats, dict) else {}
