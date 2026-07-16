"""Tenant resolver (Module 2).

Turns an inbound signal (organization id, slug, host header / custom domain, or
an explicit tenant id) into a validated, active :class:`TenantContext`. The
resolver is the *only* sanctioned way to enter a tenant scope from the edge, so
all tenant entry passes through one auditable choke point.
"""

from __future__ import annotations

from src.platform.common.errors import NotFoundError, TenantIsolationError
from src.platform.common.repository import InMemoryRepository
from src.platform.organizations.repository import OrganizationRepository
from src.platform.tenancy.context import TenantContext
from src.platform.tenancy.models import Tenant, TenantStatus


class TenantResolver:
    """Resolve inbound requests to a tenant and produce a context."""

    def __init__(
        self,
        tenants: InMemoryRepository[Tenant],
        organizations: OrganizationRepository,
    ) -> None:
        self._tenants = tenants
        self._orgs = organizations

    # -- lookups ------------------------------------------------------------

    def by_id(self, tenant_id: str) -> Tenant | None:
        """Return the tenant with ``tenant_id`` (or ``None``)."""
        return self._tenants.get(tenant_id)

    def by_organization(self, organization_id: str) -> Tenant | None:
        """Return the tenant for ``organization_id`` (id == organization id)."""
        return self._tenants.get(organization_id)

    def by_slug(self, slug: str) -> Tenant | None:
        """Return the tenant whose slug matches ``slug``."""
        matches = self._tenants.list(where=lambda t: t.slug == slug)
        return matches[0] if matches else None

    def by_domain(self, host: str) -> Tenant | None:
        """Resolve a tenant by an organization's custom domain (host header)."""
        host = host.strip().lower()
        for org in self._orgs.organizations.list():
            domain = org.branding.custom_domain.strip().lower()
            if domain and domain == host:
                return self._tenants.get(org.id)
        return None

    # -- context production -------------------------------------------------

    def resolve(
        self,
        *,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        slug: str | None = None,
        host: str | None = None,
        principal_id: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None,
    ) -> TenantContext:
        """Resolve any supported signal into an active :class:`TenantContext`.

        Raises:
            NotFoundError: If no tenant matches the supplied signal.
            TenantIsolationError: If the resolved tenant is not active.
        """
        tenant: Tenant | None = None
        if tenant_id is not None:
            tenant = self.by_id(tenant_id)
        elif organization_id is not None:
            tenant = self.by_organization(organization_id)
        elif slug is not None:
            tenant = self.by_slug(slug)
        elif host is not None:
            tenant = self.by_domain(host)

        if tenant is None:
            raise NotFoundError("could not resolve a tenant from the request")
        if tenant.status != TenantStatus.ACTIVE:
            raise TenantIsolationError(
                f"tenant '{tenant.id}' is not active (status={tenant.status.value})"
            )

        return TenantContext(
            tenant_id=tenant.id,
            organization_id=tenant.organization_id,
            principal_id=principal_id,
            session_id=session_id,
            request_id=request_id,
        )
