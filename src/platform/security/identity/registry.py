"""Identity provider registry (Module 1).

A catalogue of authentication providers keyed by
:class:`IdentityProviderType`. The local provider is registered by the manager;
the future (interface-only) providers can be discovered so an operator can see
which IdPs the platform is *ready* to integrate with.
"""

from __future__ import annotations

from src.platform.security.common.errors import IdentityError
from src.platform.security.identity.models import IdentityProviderType
from src.platform.security.identity.providers import future_providers


class IdentityProviderRegistry:
    """Registers and looks up identity providers by type."""

    def __init__(self) -> None:
        self._providers: dict[IdentityProviderType, object] = {}

    def register(self, provider) -> object:
        """Register a provider under its ``provider_type``."""
        self._providers[provider.provider_type] = provider
        return provider

    def has(self, provider_type: IdentityProviderType) -> bool:
        """Return whether a provider is registered for ``provider_type``."""
        return provider_type in self._providers

    def get(self, provider_type: IdentityProviderType) -> object:
        """Return the provider for ``provider_type`` or raise."""
        provider = self._providers.get(provider_type)
        if provider is None:
            raise IdentityError(f"no identity provider for '{provider_type.value}'")
        return provider

    def register_future_providers(self) -> "IdentityProviderRegistry":
        """Register every interface-only future IdP placeholder for discovery."""
        for provider in future_providers():
            self.register(provider)
        return self

    def types(self) -> list[IdentityProviderType]:
        """Return the registered provider types."""
        return list(self._providers)
