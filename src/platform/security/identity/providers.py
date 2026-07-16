"""Identity provider seams (Module 1).

The :class:`AuthenticationProvider` and :class:`AuthorizationProvider` interfaces
every identity backend satisfies, plus a deterministic offline
:class:`LocalIdentityProvider` and *future-ready* placeholders for Azure AD,
Okta, Auth0, Google Workspace, LDAP, SAML and OIDC. The placeholders describe
themselves (type, protocol, metadata) so wiring can target the real seam today,
but they perform **no** network calls and refuse to authenticate until a real
backend is bound.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.security.common.errors import IdentityError
from src.platform.security.identity.models import (
    Identity,
    IdentityProviderType,
)


@runtime_checkable
class AuthenticationProvider(Protocol):
    """Verifies credentials and returns the matching identity (interface only)."""

    provider_type: IdentityProviderType

    def authenticate(self, tenant_id: str, subject: str, secret: str) -> Identity | None: ...


@runtime_checkable
class AuthorizationProvider(Protocol):
    """Decides whether an identity may hold a permission (interface only)."""

    def is_authorized(self, identity: Identity, permission: str) -> bool: ...


class LocalIdentityProvider:
    """A deterministic, offline authentication provider backed by a store.

    Credentials are verified against identities registered with the
    :class:`~src.platform.security.identity.manager.IdentityManager` using a
    salted hash comparison performed by the manager — this provider only decides
    *which* identity a ``(tenant, subject)`` maps to. Offline and dependency-free.
    """

    provider_type = IdentityProviderType.LOCAL

    def __init__(self, resolver) -> None:  # resolver: (tenant, subject) -> Identity|None
        self._resolver = resolver

    def authenticate(self, tenant_id: str, subject: str, secret: str) -> Identity | None:
        """Return the identity for ``(tenant, subject)`` (secret checked upstream)."""
        return self._resolver(tenant_id, subject)


class _FutureProvider:
    """Base for future IdP placeholders — describes itself, never connects."""

    provider_type: IdentityProviderType
    protocol: str = ""

    def describe(self) -> dict[str, str]:
        """Return non-secret descriptive metadata about this provider."""
        return {
            "provider_type": self.provider_type.value,
            "protocol": self.protocol,
            "status": "interface_only",
        }

    def authenticate(self, tenant_id: str, subject: str, secret: str) -> Identity | None:
        raise IdentityError(
            f"{self.provider_type.value} provider is an architecture placeholder; "
            "bind a real backend before use",
            code="identity_provider_not_configured",
        )


class AzureAdProvider(_FutureProvider):
    provider_type = IdentityProviderType.AZURE_AD
    protocol = "oidc"


class OktaProvider(_FutureProvider):
    provider_type = IdentityProviderType.OKTA
    protocol = "oidc"


class Auth0Provider(_FutureProvider):
    provider_type = IdentityProviderType.AUTH0
    protocol = "oidc"


class GoogleWorkspaceProvider(_FutureProvider):
    provider_type = IdentityProviderType.GOOGLE_WORKSPACE
    protocol = "oidc"


class LdapProvider(_FutureProvider):
    provider_type = IdentityProviderType.LDAP
    protocol = "ldap"


class SamlProvider(_FutureProvider):
    provider_type = IdentityProviderType.SAML
    protocol = "saml2"


class OidcProvider(_FutureProvider):
    provider_type = IdentityProviderType.OIDC
    protocol = "oidc"


def future_providers() -> list[_FutureProvider]:
    """Return one instance of every future (interface-only) IdP placeholder."""
    return [
        AzureAdProvider(),
        OktaProvider(),
        Auth0Provider(),
        GoogleWorkspaceProvider(),
        LdapProvider(),
        SamlProvider(),
        OidcProvider(),
    ]
