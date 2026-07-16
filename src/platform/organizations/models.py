"""Organization domain models (Module 1).

The :class:`Organization` is the root aggregate of the platform: every tenant
maps 1:1 to exactly one organization, and every other resource ultimately
belongs to one. Organizations own a hierarchy of business units, departments and
offices, plus their own settings, branding, limits and feature toggles.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import Entity, Metadata, PlatformModel, TenantScopedEntity


class OrganizationStatus(str, Enum):
    """Lifecycle state of an organization."""

    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class Location(PlatformModel):
    """A physical address / geographic location value object."""

    line1: str = ""
    line2: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    postal_code: str = ""
    timezone: str = "UTC"


class OrganizationSettings(PlatformModel):
    """Organization-wide default settings.

    Regional and security defaults that every workspace inherits unless
    overridden. Kept deliberately declarative — no behaviour, just policy.
    """

    default_timezone: str = "UTC"
    default_locale: str = "en-US"
    default_language: str = "en"
    date_format: str = "YYYY-MM-DD"
    currency: str = "USD"
    data_region: str = "global"
    enforce_mfa: bool = False
    session_timeout_minutes: int = 480
    allow_self_signup: bool = False


class OrganizationBranding(PlatformModel):
    """White-label branding for an organization."""

    display_name: str = ""
    logo_url: str = ""
    favicon_url: str = ""
    primary_color: str = "#4F46E5"
    secondary_color: str = "#0EA5E9"
    accent_color: str = "#22C55E"
    email_from_name: str = "TalentMind"
    custom_domain: str = ""


class OrganizationLimits(PlatformModel):
    """Hard resource ceilings for an organization.

    Enforced by the tenancy/subscription layers; ``None`` means "unlimited".
    """

    max_users: int | None = 25
    max_workspaces: int | None = 5
    max_projects: int | None = 50
    max_storage_gb: int | None = 25
    max_ai_credits_monthly: int | None = 10_000
    max_api_requests_per_minute: int | None = 120


class OrganizationFeatures(PlatformModel):
    """Feature availability at the organization level.

    A small set of first-class flags plus an open ``extra`` map so features can
    be added without a schema change. Resolution helper :meth:`enabled` treats
    unknown flags as disabled.
    """

    sso: bool = False
    scim_provisioning: bool = False
    audit_export: bool = False
    api_access: bool = True
    custom_branding: bool = False
    advanced_rbac: bool = True
    ai_copilot: bool = True
    extra: dict[str, bool] = Field(default_factory=dict)

    def enabled(self, name: str) -> bool:
        """Return whether feature ``name`` is on (first-class or ``extra``)."""
        if name in type(self).model_fields and name != "extra":
            return bool(getattr(self, name))
        return bool(self.extra.get(name, False))


class Organization(Entity):
    """Root aggregate: a customer organization.

    Attributes:
        slug: URL/DNS-safe unique handle.
        legal_name: Registered legal entity name.
        display_name: Human-facing name.
        status: Lifecycle state.
        primary_location: Headquarters / billing location.
        settings / branding / limits / features / metadata: owned sub-objects.
    """

    slug: str
    legal_name: str
    display_name: str
    status: OrganizationStatus = OrganizationStatus.TRIAL
    primary_location: Location = Field(default_factory=Location)
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)
    branding: OrganizationBranding = Field(default_factory=OrganizationBranding)
    limits: OrganizationLimits = Field(default_factory=OrganizationLimits)
    features: OrganizationFeatures = Field(default_factory=OrganizationFeatures)
    metadata: Metadata = Field(default_factory=Metadata)

    def is_operational(self) -> bool:
        """Return whether the organization may be used (trial or active)."""
        return self.status in (OrganizationStatus.TRIAL, OrganizationStatus.ACTIVE)


class BusinessUnit(TenantScopedEntity):
    """A top-level division within an organization (e.g. "EMEA", "R&D")."""

    name: str
    code: str = ""
    head_user_id: str | None = None
    description: str = ""


class Department(TenantScopedEntity):
    """A department nested under a business unit (e.g. "Talent Acquisition")."""

    name: str
    code: str = ""
    business_unit_id: str | None = None
    head_user_id: str | None = None


class Office(TenantScopedEntity):
    """A physical office / site belonging to an organization."""

    name: str
    location: Location = Field(default_factory=Location)
    is_headquarters: bool = False
