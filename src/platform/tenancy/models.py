"""Tenant domain models (Module 2).

A **tenant** is the runtime isolation unit of the platform. It maps 1:1 to an
:class:`~src.platform.organizations.models.Organization`; by convention the
tenant's ``id`` equals the organization id, so the ``tenant_id`` carried by every
:class:`~src.platform.common.models.TenantScopedEntity` is exactly the owning
organization id. This single, consistent isolation key is what makes
cross-tenant leakage structurally impossible.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import Entity, PlatformModel


class TenantStatus(str, Enum):
    """Runtime state of a tenant."""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPROVISIONING = "deprovisioning"


class IsolationMode(str, Enum):
    """How a tenant's data is physically isolated.

    * ``SHARED`` — shared store, logically partitioned by ``tenant_id`` (default;
      the model this in-memory reference implementation follows).
    * ``SCHEMA`` — dedicated schema per tenant on shared infrastructure.
    * ``DEDICATED`` — fully dedicated store per tenant (enterprise tier).
    """

    SHARED = "shared"
    SCHEMA = "schema"
    DEDICATED = "dedicated"


class TenantLimits(PlatformModel):
    """Effective runtime limits for a tenant (may override org limits)."""

    max_users: int | None = 25
    max_workspaces: int | None = 5
    max_storage_gb: int | None = 25
    max_ai_credits_monthly: int | None = 10_000
    max_requests_per_minute: int | None = 120
    max_concurrent_sessions: int | None = 100


class TenantFeatures(PlatformModel):
    """Feature toggles resolved for a tenant."""

    values: dict[str, bool] = Field(default_factory=dict)

    def enabled(self, name: str) -> bool:
        """Return whether feature ``name`` is enabled for this tenant."""
        return bool(self.values.get(name, False))


class TenantConfiguration(PlatformModel):
    """Physical/routing configuration for a tenant.

    Attributes:
        isolation_mode: How the tenant is isolated.
        data_region: Region the tenant's data resides in.
        storage_prefix: Namespace prefix for the tenant's storage keys.
        cache_namespace: Namespace prefix for the tenant's cache keys.
        shard_key: Optional shard/partition hint for horizontal scaling.
    """

    isolation_mode: IsolationMode = IsolationMode.SHARED
    data_region: str = "global"
    storage_prefix: str = ""
    cache_namespace: str = ""
    shard_key: str = ""


class Tenant(Entity):
    """A provisioned tenant (1:1 with an organization).

    Attributes:
        organization_id: Owning organization (equals ``id`` by convention).
        slug: Copied from the organization for convenient routing.
        status: Runtime state.
        configuration / features / limits: resolved tenant policy.
    """

    organization_id: str
    slug: str
    status: TenantStatus = TenantStatus.ACTIVE
    configuration: TenantConfiguration = Field(default_factory=TenantConfiguration)
    features: TenantFeatures = Field(default_factory=TenantFeatures)
    limits: TenantLimits = Field(default_factory=TenantLimits)

    @property
    def tenant_id(self) -> str:
        """The isolation key for this tenant (equal to :attr:`id`)."""
        return self.id

    def is_active(self) -> bool:
        """Return whether the tenant may serve traffic."""
        return self.status == TenantStatus.ACTIVE
