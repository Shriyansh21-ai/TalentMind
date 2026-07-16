"""Organization application service (Module 1).

The single public entry point for organization lifecycle operations. It owns
invariants (unique slug, valid hierarchy references, tenant scoping of children)
and delegates storage to :class:`OrganizationRepository`. Business logic here is
strictly enterprise-structural — it never touches hiring logic.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import ConflictError, PlatformValidationError
from src.platform.common.ids import generate_id, slugify
from src.platform.organizations.models import (
    BusinessUnit,
    Department,
    Location,
    Office,
    Organization,
    OrganizationBranding,
    OrganizationFeatures,
    OrganizationLimits,
    OrganizationSettings,
    OrganizationStatus,
)
from src.platform.organizations.repository import OrganizationRepository


class OrganizationService:
    """Create and manage organizations and their internal hierarchy."""

    def __init__(
        self,
        repository: OrganizationRepository | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.repo = repository or OrganizationRepository()
        self._clock = clock or SystemClock()

    # -- organizations ------------------------------------------------------

    def create_organization(
        self,
        legal_name: str,
        *,
        display_name: str | None = None,
        slug: str | None = None,
        status: OrganizationStatus = OrganizationStatus.TRIAL,
        settings: OrganizationSettings | None = None,
        branding: OrganizationBranding | None = None,
        limits: OrganizationLimits | None = None,
        features: OrganizationFeatures | None = None,
        primary_location: Location | None = None,
    ) -> Organization:
        """Create an organization, enforcing a unique slug.

        Raises:
            PlatformValidationError: If ``legal_name`` is blank.
            ConflictError: If the derived/explicit slug already exists.
        """
        if not legal_name.strip():
            raise PlatformValidationError("organization legal_name is required")
        resolved_slug = slugify(slug or legal_name)
        if self.repo.by_slug(resolved_slug) is not None:
            raise ConflictError(f"organization slug '{resolved_slug}' already in use")

        now = self._clock.now()
        org = Organization(
            id=generate_id("org"),
            slug=resolved_slug,
            legal_name=legal_name,
            display_name=display_name or legal_name,
            status=status,
            settings=settings or OrganizationSettings(),
            branding=branding or OrganizationBranding(display_name=display_name or legal_name),
            limits=limits or OrganizationLimits(),
            features=features or OrganizationFeatures(),
            primary_location=primary_location or Location(),
            created_at=now,
            updated_at=now,
        )
        return self.repo.organizations.add(org)

    def get_organization(self, organization_id: str) -> Organization | None:
        """Return an organization by id (or ``None``)."""
        return self.repo.organizations.get(organization_id)

    def require_organization(self, organization_id: str) -> Organization:
        """Return an organization by id or raise :class:`NotFoundError`."""
        return self.repo.organizations.require(organization_id)

    def list_organizations(self) -> list[Organization]:
        """Return all organizations (platform-admin scope)."""
        return self.repo.organizations.list()

    def set_status(self, organization_id: str, status: OrganizationStatus) -> Organization:
        """Transition an organization to ``status``."""
        org = self.repo.organizations.require(organization_id)
        org.status = status
        org.touch(self._clock.now())
        return self.repo.organizations.update(org)

    def update_settings(
        self, organization_id: str, settings: OrganizationSettings
    ) -> Organization:
        """Replace an organization's settings."""
        org = self.repo.organizations.require(organization_id)
        org.settings = settings
        org.touch(self._clock.now())
        return self.repo.organizations.update(org)

    def update_branding(
        self, organization_id: str, branding: OrganizationBranding
    ) -> Organization:
        """Replace an organization's branding."""
        org = self.repo.organizations.require(organization_id)
        org.branding = branding
        org.touch(self._clock.now())
        return self.repo.organizations.update(org)

    def update_limits(
        self, organization_id: str, limits: OrganizationLimits
    ) -> Organization:
        """Replace an organization's resource limits."""
        org = self.repo.organizations.require(organization_id)
        org.limits = limits
        org.touch(self._clock.now())
        return self.repo.organizations.update(org)

    # -- hierarchy ----------------------------------------------------------

    def _scope(self, organization_id: str) -> Organization:
        """Return the org, guaranteeing it exists before adding children."""
        return self.repo.organizations.require(organization_id)

    def add_business_unit(
        self, organization_id: str, name: str, *, code: str = "", description: str = ""
    ) -> BusinessUnit:
        """Add a business unit to an organization."""
        org = self._scope(organization_id)
        unit = BusinessUnit(
            id=generate_id("bu"),
            tenant_id=org.id,
            organization_id=org.id,
            name=name,
            code=code,
            description=description,
        )
        return self.repo.business_units.add(unit)

    def add_department(
        self,
        organization_id: str,
        name: str,
        *,
        business_unit_id: str | None = None,
        code: str = "",
    ) -> Department:
        """Add a department, optionally nested under a business unit."""
        org = self._scope(organization_id)
        if business_unit_id is not None:
            # Isolation-checked existence: unit must belong to this org.
            self.repo.business_units.require(business_unit_id, tenant_id=org.id)
        dept = Department(
            id=generate_id("dept"),
            tenant_id=org.id,
            organization_id=org.id,
            name=name,
            code=code,
            business_unit_id=business_unit_id,
        )
        return self.repo.departments.add(dept)

    def add_office(
        self,
        organization_id: str,
        name: str,
        *,
        location: Location | None = None,
        is_headquarters: bool = False,
    ) -> Office:
        """Add a physical office to an organization."""
        org = self._scope(organization_id)
        office = Office(
            id=generate_id("office"),
            tenant_id=org.id,
            organization_id=org.id,
            name=name,
            location=location or Location(),
            is_headquarters=is_headquarters,
        )
        return self.repo.offices.add(office)

    def business_units(self, organization_id: str) -> list[BusinessUnit]:
        """Return the organization's business units."""
        return self.repo.business_units.list(tenant_id=organization_id)

    def departments(self, organization_id: str) -> list[Department]:
        """Return the organization's departments."""
        return self.repo.departments.list(tenant_id=organization_id)

    def offices(self, organization_id: str) -> list[Office]:
        """Return the organization's offices."""
        return self.repo.offices.list(tenant_id=organization_id)
