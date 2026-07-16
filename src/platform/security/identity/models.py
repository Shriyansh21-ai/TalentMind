"""Enterprise identity models (Module 1).

The identity vocabulary: an :class:`Identity` (a tenant-scoped principal backed
by some provider), its :class:`IdentityMetadata`, the runtime
:class:`IdentityContext` threaded through authenticated calls, and the
:class:`IdentitySession` / :class:`IdentityToken` issued on login. Designed to
be future-ready for Azure AD, Okta, Auth0, Google Workspace, LDAP, SAML and OIDC
without any real integration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity


class IdentityProviderType(str, Enum):
    """The identity provider backing an identity (future-ready)."""

    LOCAL = "local"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    AUTH0 = "auth0"
    GOOGLE_WORKSPACE = "google_workspace"
    LDAP = "ldap"
    SAML = "saml"
    OIDC = "oidc"


class IdentityStatus(str, Enum):
    """The lifecycle state of an identity."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"

    @property
    def can_authenticate(self) -> bool:
        """Return whether an identity in this state may authenticate."""
        return self == IdentityStatus.ACTIVE


class IdentityMetadata(PlatformModel):
    """Descriptive, provider-supplied metadata for an identity."""

    display_name: str = ""
    email: str = ""
    external_id: str = ""  # id in the upstream IdP (never a secret)
    attributes: dict[str, object] = Field(default_factory=dict)


class Identity(TenantScopedEntity):
    """A tenant-scoped principal backed by an identity provider."""

    subject: str  # stable subject/username within the provider
    provider_type: IdentityProviderType = IdentityProviderType.LOCAL
    status: IdentityStatus = IdentityStatus.PENDING
    metadata: IdentityMetadata = Field(default_factory=IdentityMetadata)
    groups: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    last_authenticated_at: datetime | None = None


class IdentityToken(PlatformModel):
    """An opaque, hashed access token issued to a session.

    The plaintext ``value`` is returned to the caller exactly once at issue time;
    only ``token_hash`` is persisted, so a leaked store never reveals a token.
    """

    token_hash: str
    token_type: str = "bearer"
    issued_at: datetime
    expires_at: datetime
    claims: dict[str, object] = Field(default_factory=dict)


class IdentitySession(TenantScopedEntity):
    """A tenant-scoped authenticated session for an identity."""

    identity_id: str
    subject: str = ""
    token: IdentityToken
    active: bool = True
    revoked_at: datetime | None = None

    def is_valid_at(self, moment: datetime) -> bool:
        """Return whether the session is active and unexpired at ``moment``."""
        return self.active and moment < self.token.expires_at


class IdentityContext(PlatformModel):
    """The runtime identity context threaded through authenticated calls."""

    identity_id: str
    tenant_id: str
    subject: str = ""
    provider_type: IdentityProviderType = IdentityProviderType.LOCAL
    roles: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    attributes: dict[str, object] = Field(default_factory=dict)
    session_id: str = ""

    def has_role(self, role: str) -> bool:
        """Return whether the context carries ``role``."""
        return role in self.roles

    def attribute(self, key: str, default: object = None) -> object:
        """Return an identity attribute (or ``default``)."""
        return self.attributes.get(key, default)
