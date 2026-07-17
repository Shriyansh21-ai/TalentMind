"""Integration registry & provider discovery (Module 1 · Module 13).

The :class:`IntegrationRegistry` is the single catalogue of every provider the
platform knows about. Providers register themselves (or are discovered lazily
from the built-in provider packages), and the registry exposes them by key and
by category. Definitions are **cached** after first computation so the catalogue
is cheap to read repeatedly (Module 13 — performance).

Discovery is *lazy*: the registry does not import the HRIS/ATS/etc. provider
packages until :meth:`discover_builtins` is called, keeping module import light.
"""

from __future__ import annotations

from collections.abc import Callable

from src.platform.common.errors import ConflictError
from src.platform.integrations.common.errors import ProviderNotFoundError
from src.platform.integrations.common.models import (
    IntegrationDefinition,
    ProviderCategory,
)
from src.platform.integrations.common.provider import IntegrationProvider


class IntegrationRegistry:
    """A cached catalogue of integration providers, grouped by category."""

    def __init__(self) -> None:
        self._providers: dict[str, IntegrationProvider] = {}
        self._definition_cache: dict[str, IntegrationDefinition] = {}
        self._discovered = False

    # -- registration -------------------------------------------------------

    def register(self, provider: IntegrationProvider) -> IntegrationProvider:
        """Register a provider under its ``key`` (idempotent-safe on identity)."""
        key = provider.key
        existing = self._providers.get(key)
        if existing is not None and existing is not provider:
            raise ConflictError(f"provider '{key}' already registered")
        self._providers[key] = provider
        self._definition_cache.pop(key, None)  # invalidate cache for this key
        return provider

    def register_all(self, providers: list[IntegrationProvider]) -> list[IntegrationProvider]:
        """Register a batch of providers."""
        return [self.register(p) for p in providers]

    # -- lookup -------------------------------------------------------------

    def has(self, key: str) -> bool:
        """Return whether a provider is registered under ``key``."""
        return key in self._providers

    def get(self, key: str) -> IntegrationProvider:
        """Return a provider by key or raise :class:`ProviderNotFoundError`."""
        provider = self._providers.get(key)
        if provider is None:
            raise ProviderNotFoundError(f"no integration provider '{key}' registered")
        return provider

    def definition(self, key: str) -> IntegrationDefinition:
        """Return the (cached) catalogue definition for a provider key."""
        if key not in self._definition_cache:
            self._definition_cache[key] = self.get(key).describe()
        return self._definition_cache[key]

    def definitions(
        self, *, category: ProviderCategory | None = None
    ) -> list[IntegrationDefinition]:
        """Return all catalogue definitions, optionally filtered by category."""
        defs = [self.definition(key) for key in self._providers]
        if category is not None:
            defs = [d for d in defs if d.category == category]
        return sorted(defs, key=lambda d: d.metadata.display_name.lower())

    def providers(self, *, category: ProviderCategory | None = None) -> list[IntegrationProvider]:
        """Return all registered providers, optionally filtered by category."""
        result = list(self._providers.values())
        if category is not None:
            result = [p for p in result if p.category == category]
        return result

    def keys(self) -> list[str]:
        """Return every registered provider key (registration order)."""
        return list(self._providers)

    def categories(self) -> dict[ProviderCategory, int]:
        """Return a count of registered providers per category."""
        counts: dict[ProviderCategory, int] = {}
        for provider in self._providers.values():
            counts[provider.category] = counts.get(provider.category, 0) + 1
        return counts

    # -- discovery (lazy) ---------------------------------------------------

    def discover_builtins(self) -> IntegrationRegistry:
        """Lazily import and register every built-in provider package.

        Import happens here (not at module load) so pulling in the registry
        stays cheap. Safe to call repeatedly — providers register at most once.
        """
        if self._discovered:
            return self
        loaders: list[Callable[[], list[IntegrationProvider]]] = []

        from src.platform.integrations.ats.providers import all_providers as _ats
        from src.platform.integrations.calendar.providers import (
            all_providers as _cal,
        )
        from src.platform.integrations.communication.providers import (
            all_providers as _comm,
        )
        from src.platform.integrations.documents.providers import (
            all_providers as _docs,
        )
        from src.platform.integrations.hris.providers import all_providers as _hris

        loaders.extend([_hris, _ats, _cal, _comm, _docs])
        for loader in loaders:
            self.register_all(loader())
        self._discovered = True
        return self


def build_default_registry() -> IntegrationRegistry:
    """Return a registry pre-loaded with every built-in provider."""
    return IntegrationRegistry().discover_builtins()
