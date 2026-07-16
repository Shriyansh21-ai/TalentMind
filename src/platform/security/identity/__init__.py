"""Module 1 — Enterprise Identity Framework.

Identity manager, context, providers (local + future-ready Azure AD / Okta /
Auth0 / Google Workspace / LDAP / SAML / OIDC placeholders), registry, metadata,
sessions, tokens and lifecycle. Deterministic and offline — no real IdP calls.
"""

from __future__ import annotations

from src.platform.security.identity.manager import IdentityManager
from src.platform.security.identity.models import (
    Identity,
    IdentityContext,
    IdentityMetadata,
    IdentityProviderType,
    IdentitySession,
    IdentityStatus,
    IdentityToken,
)
from src.platform.security.identity.providers import (
    AuthenticationProvider,
    AuthorizationProvider,
    LocalIdentityProvider,
    future_providers,
)
from src.platform.security.identity.registry import IdentityProviderRegistry

__all__ = [
    "IdentityProviderType",
    "IdentityStatus",
    "IdentityMetadata",
    "Identity",
    "IdentityToken",
    "IdentitySession",
    "IdentityContext",
    "AuthenticationProvider",
    "AuthorizationProvider",
    "LocalIdentityProvider",
    "future_providers",
    "IdentityProviderRegistry",
    "IdentityManager",
]
