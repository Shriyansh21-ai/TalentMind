"""API gateway authentication & rate-limit hooks (Module 7).

Seams the gateway calls on every request: an :class:`AuthenticationHook` that
turns raw request credentials into an authenticated :class:`ApiPrincipal`, and a
:class:`RateLimitHook` the gateway consults before dispatch. Interfaces plus
offline reference implementations — no real token verification or distributed
rate limiting is performed.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.models import PlatformModel


class ApiPrincipal(PlatformModel):
    """The authenticated identity behind an API request."""

    principal_id: str
    tenant_id: str
    scopes: list[str] = Field(default_factory=list)
    authenticated: bool = True

    def has_scope(self, scope: str) -> bool:
        """Return whether the principal holds ``scope`` (``*`` is a wildcard)."""
        return "*" in self.scopes or scope in self.scopes


@runtime_checkable
class AuthenticationHook(Protocol):
    """Turns request credentials into a principal (interface only)."""

    def authenticate(self, headers: dict[str, str]) -> ApiPrincipal | None: ...


class StaticApiKeyAuthHook:
    """Offline reference auth: maps an ``X-Api-Key`` header to a principal.

    Deterministic and offline — for tests and demos only. Real deployments bind
    a JWT/OIDC/session verifier at this seam.
    """

    def __init__(self) -> None:
        self._keys: dict[str, ApiPrincipal] = {}

    def register_key(self, api_key: str, principal: ApiPrincipal) -> None:
        """Associate an API key with a principal."""
        self._keys[api_key] = principal

    def authenticate(self, headers: dict[str, str]) -> ApiPrincipal | None:
        """Return the principal for the request's ``X-Api-Key`` (or ``None``)."""
        key = headers.get("X-Api-Key") or headers.get("x-api-key", "")
        return self._keys.get(key)


@runtime_checkable
class RateLimitHook(Protocol):
    """Consulted before dispatch; returns whether the request may proceed."""

    def allow(self, principal_id: str) -> bool: ...
