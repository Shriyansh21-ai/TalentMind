"""Tenant isolation guard (Module 2 / Module 15).

A thin, reusable enforcement point that other layers call to guarantee an
operation stays inside its tenant boundary. The repository layer already refuses
cross-tenant reads/writes; this guard covers the cases the repository can't see
— comparing a loaded entity against the *active context*, and namespacing cache
and storage keys so two tenants can never collide.
"""

from __future__ import annotations

from src.platform.common.errors import TenantIsolationError
from src.platform.common.models import TenantScopedEntity
from src.platform.tenancy.context import TenantContext, require_context


class TenantIsolationGuard:
    """Assertions that enforce the tenant boundary (Zero Trust default)."""

    @staticmethod
    def assert_entity_in_scope(
        entity: TenantScopedEntity, context: TenantContext | None = None
    ) -> None:
        """Raise if ``entity`` does not belong to the active/given tenant."""
        ctx = context or require_context()
        if entity.tenant_id != ctx.tenant_id:
            raise TenantIsolationError(
                f"entity '{entity.id}' (tenant {entity.tenant_id!r}) is outside "
                f"active tenant {ctx.tenant_id!r}"
            )

    @staticmethod
    def assert_tenant_matches(tenant_id: str, context: TenantContext | None = None) -> None:
        """Raise if ``tenant_id`` differs from the active/given tenant."""
        ctx = context or require_context()
        if tenant_id != ctx.tenant_id:
            raise TenantIsolationError(
                f"tenant {tenant_id!r} does not match active tenant {ctx.tenant_id!r}"
            )

    @staticmethod
    def namespaced_key(tenant_id: str, key: str) -> str:
        """Return a tenant-prefixed key for cache/storage isolation."""
        return f"t:{tenant_id}:{key}"
