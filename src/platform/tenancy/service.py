"""Tenant application service (Module 2).

Provisions and manages the lifecycle of tenants, and wires together the tenant
runtime primitives (resolver, cache, storage, middleware, isolation guard). A
tenant is provisioned *from* an organization, inheriting its slug and limits, so
the org→tenant mapping stays 1:1 and consistent.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import ConflictError
from src.platform.common.repository import InMemoryRepository
from src.platform.organizations.models import Organization
from src.platform.organizations.repository import OrganizationRepository
from src.platform.tenancy.cache import TenantCache
from src.platform.tenancy.middleware import TenantMiddleware
from src.platform.tenancy.models import (
    IsolationMode,
    Tenant,
    TenantConfiguration,
    TenantFeatures,
    TenantLimits,
    TenantStatus,
)
from src.platform.tenancy.resolver import TenantResolver
from src.platform.tenancy.storage import TenantStorage


class TenantService:
    """Create, resolve and manage tenants."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        *,
        tenants: InMemoryRepository[Tenant] | None = None,
        cache: TenantCache | None = None,
        storage: TenantStorage | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._orgs = organizations
        self.tenants: InMemoryRepository[Tenant] = tenants or InMemoryRepository("tenant")
        self.cache = cache or TenantCache()
        self.storage = storage or TenantStorage()
        self._clock = clock or SystemClock()
        self.resolver = TenantResolver(self.tenants, organizations)
        self.middleware = TenantMiddleware(self.resolver)

    def provision(
        self,
        organization: Organization,
        *,
        isolation_mode: IsolationMode = IsolationMode.SHARED,
    ) -> Tenant:
        """Provision the tenant for ``organization`` (idempotent per org).

        The tenant id equals the organization id, keeping the isolation key
        consistent with every :class:`TenantScopedEntity`.

        Raises:
            ConflictError: If a tenant already exists for the organization.
        """
        if self.tenants.get(organization.id) is not None:
            raise ConflictError(f"tenant for org '{organization.id}' already provisioned")

        limits = organization.limits
        now = self._clock.now()
        tenant = Tenant(
            id=organization.id,
            organization_id=organization.id,
            slug=organization.slug,
            status=TenantStatus.ACTIVE,
            configuration=TenantConfiguration(
                isolation_mode=isolation_mode,
                data_region=organization.settings.data_region,
                storage_prefix=organization.slug,
                cache_namespace=organization.slug,
                shard_key=organization.slug,
            ),
            features=TenantFeatures(
                values={
                    "sso": organization.features.sso,
                    "api_access": organization.features.api_access,
                    "ai_copilot": organization.features.ai_copilot,
                    "custom_branding": organization.features.custom_branding,
                    "advanced_rbac": organization.features.advanced_rbac,
                }
            ),
            limits=TenantLimits(
                max_users=limits.max_users,
                max_workspaces=limits.max_workspaces,
                max_storage_gb=limits.max_storage_gb,
                max_ai_credits_monthly=limits.max_ai_credits_monthly,
                max_requests_per_minute=limits.max_api_requests_per_minute,
            ),
            created_at=now,
            updated_at=now,
        )
        return self.tenants.add(tenant)

    def get(self, tenant_id: str) -> Tenant | None:
        """Return a tenant by id (or ``None``)."""
        return self.tenants.get(tenant_id)

    def require(self, tenant_id: str) -> Tenant:
        """Return a tenant by id or raise :class:`NotFoundError`."""
        return self.tenants.require(tenant_id)

    def list(self) -> list[Tenant]:
        """Return all tenants (platform-admin scope)."""
        return self.tenants.list()

    def set_status(self, tenant_id: str, status: TenantStatus) -> Tenant:
        """Transition a tenant's runtime status and invalidate its cache."""
        tenant = self.tenants.require(tenant_id)
        tenant.status = status
        tenant.touch(self._clock.now())
        self.cache.invalidate(tenant_id)
        return self.tenants.update(tenant)
