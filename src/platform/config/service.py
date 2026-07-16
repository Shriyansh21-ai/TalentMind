"""Configuration service (Module 6 / Module 14).

Owns each tenant's :class:`Configuration` and answers hot questions — "is this
feature enabled?", "is the tenant licensed for X?" — behind a configuration
cache so repeated lookups don't rebuild state. Any mutation invalidates the
tenant's cache entry, keeping reads consistent.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import FeatureDisabledError, NotFoundError
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.config.models import (
    Configuration,
    License,
)
from src.platform.tenancy.cache import TenantCache

_CACHE_KEY = "configuration"


class ConfigurationService:
    """Manage and cache per-tenant configuration."""

    def __init__(
        self,
        *,
        repository: InMemoryRepository[Configuration] | None = None,
        cache: TenantCache | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.repo = repository or InMemoryRepository("configuration")
        self.cache = cache or TenantCache()
        self._clock = clock or SystemClock()

    # -- lifecycle ----------------------------------------------------------

    def ensure(self, tenant_id: str, organization_id: str) -> Configuration:
        """Return the tenant's configuration, creating a default if absent."""
        existing = self.repo.list(tenant_id=tenant_id)
        if existing:
            return existing[0]
        now = self._clock.now()
        config = Configuration(
            id=generate_id("cfg"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            created_at=now,
            updated_at=now,
        )
        self.repo.add(config)
        self.cache.set(tenant_id, _CACHE_KEY, config)
        return config

    def get(self, tenant_id: str) -> Configuration | None:
        """Return the tenant's configuration from cache or store (or ``None``)."""
        cached = self.cache.get(tenant_id, _CACHE_KEY)
        if cached is not None:
            return cached
        found = self.repo.list(tenant_id=tenant_id)
        if not found:
            return None
        self.cache.set(tenant_id, _CACHE_KEY, found[0])
        return found[0]

    def _save(self, config: Configuration) -> Configuration:
        """Persist a configuration change and refresh the cache."""
        config.touch(self._clock.now())
        self.repo.update(config)
        self.cache.invalidate(config.tenant_id, _CACHE_KEY)
        self.cache.set(config.tenant_id, _CACHE_KEY, config)
        return config

    # -- feature flags ------------------------------------------------------

    def set_feature(self, tenant_id: str, key: str, enabled: bool) -> Configuration:
        """Enable/disable a feature flag for a tenant."""
        config = self.repo.require(self._require_id(tenant_id), tenant_id=tenant_id)
        config.feature_flags = {**config.feature_flags, key: enabled}
        return self._save(config)

    def is_feature_enabled(self, tenant_id: str, key: str) -> bool:
        """Return whether a feature flag is enabled (defaults to ``False``)."""
        config = self.get(tenant_id)
        return bool(config.feature_flags.get(key, False)) if config else False

    def require_feature(self, tenant_id: str, key: str) -> None:
        """Raise :class:`FeatureDisabledError` unless the feature is enabled."""
        if not self.is_feature_enabled(tenant_id, key):
            raise FeatureDisabledError(f"feature '{key}' is not enabled")

    # -- licensing ----------------------------------------------------------

    def set_license(self, tenant_id: str, license_: License) -> Configuration:
        """Replace a tenant's license."""
        config = self.repo.require(self._require_id(tenant_id), tenant_id=tenant_id)
        config.license = license_
        return self._save(config)

    def is_licensed_for(self, tenant_id: str, entitlement: str) -> bool:
        """Return whether the tenant's active license includes ``entitlement``."""
        config = self.get(tenant_id)
        if config is None:
            return False
        lic = config.license
        return lic.is_valid_at(self._clock.now()) and entitlement in lic.entitlements

    # -- bundled settings ---------------------------------------------------

    def update(self, tenant_id: str, **sections) -> Configuration:
        """Update one or more configuration sections in a single call.

        Accepts keyword sections named after :class:`Configuration` fields
        (``localization=``, ``regional=``, ``ai_provider=``, ``model=``,
        ``custom_prompts=``, ``usage_limits=``).
        """
        config = self.repo.require(self._require_id(tenant_id), tenant_id=tenant_id)
        for name, value in sections.items():
            if name in Configuration.model_fields:
                setattr(config, name, value)
        return self._save(config)

    def _require_id(self, tenant_id: str) -> str:
        """Return the configuration id for a tenant, creating one if needed."""
        found = self.repo.list(tenant_id=tenant_id)
        if found:
            return found[0].id
        raise NotFoundError(
            f"no configuration provisioned for tenant '{tenant_id}' (call ensure())"
        )
