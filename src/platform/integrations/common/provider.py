"""Provider seam & base class (Module 1 · Module 18 — Provider Pattern).

Every integration — HRIS, ATS, calendar, communication, document — is modelled
as an :class:`IntegrationProvider`. A provider is a *swappable* unit: it
declares who it is (:class:`IntegrationMetadata`), what it can do
(:class:`IntegrationCapabilities`), validates a tenant's configuration and
reports its health. It performs **no** real network I/O in this milestone — the
seam is defined so a production provider can be dropped in behind it without any
caller changing.

:class:`BaseIntegrationProvider` supplies the boilerplate (describe, default
health) so concrete providers stay tiny and declarative.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.integrations.common.errors import ProviderConfigurationError
from src.platform.integrations.common.models import (
    HealthState,
    IntegrationCapabilities,
    IntegrationConfiguration,
    IntegrationDefinition,
    IntegrationHealth,
    IntegrationMetadata,
    ProviderCategory,
)


@runtime_checkable
class IntegrationProvider(Protocol):
    """The contract every integration provider satisfies (interface only)."""

    key: str
    metadata: IntegrationMetadata
    capabilities: IntegrationCapabilities

    def describe(self) -> IntegrationDefinition: ...
    def validate_configuration(self, configuration: IntegrationConfiguration) -> None: ...
    def check_health(self, configuration: IntegrationConfiguration) -> IntegrationHealth: ...


class BaseIntegrationProvider:
    """Reusable base implementing the common provider boilerplate.

    Concrete providers set :attr:`key`, :attr:`metadata` and
    :attr:`capabilities` (usually as class attributes) and optionally override
    :meth:`validate_configuration` / :meth:`check_health`. Because no real
    connection is made, the default health is a synthetic ``UNKNOWN`` snapshot —
    a real provider would probe the remote system here.
    """

    #: Unique, url-safe provider key, e.g. ``"workday"``. Set by subclasses.
    key: str = ""
    #: Descriptive metadata. Set by subclasses.
    metadata: IntegrationMetadata
    #: Declared capabilities. Set by subclasses.
    capabilities: IntegrationCapabilities

    def __init__(self) -> None:
        if not self.key:
            raise ProviderConfigurationError(
                f"{type(self).__name__} must define a non-empty 'key'"
            )

    @property
    def category(self) -> ProviderCategory:
        """Return the provider's ecosystem category."""
        return self.metadata.category

    def describe(self) -> IntegrationDefinition:
        """Return the catalogue blueprint for this provider."""
        return IntegrationDefinition(
            key=self.key,
            metadata=self.metadata,
            capabilities=self.capabilities,
        )

    def validate_configuration(
        self, configuration: IntegrationConfiguration
    ) -> None:
        """Validate a tenant configuration against this provider's needs.

        The base implementation checks that every scope the tenant enabled is
        one the provider actually declares. Subclasses add provider-specific
        required-setting checks.
        """
        declared = set(self.capabilities.scopes)
        if declared:
            unknown = [s for s in configuration.enabled_scopes if s not in declared]
            if unknown:
                raise ProviderConfigurationError(
                    f"{self.key}: unsupported scopes requested: {unknown}"
                )
        if configuration.sync_enabled and not (
            self.capabilities.supports_full_sync
            or self.capabilities.supports_incremental_sync
        ):
            raise ProviderConfigurationError(
                f"{self.key} does not support synchronization"
            )
        if configuration.webhook_enabled and not self.capabilities.supports_webhooks:
            raise ProviderConfigurationError(f"{self.key} does not support webhooks")

    def check_health(
        self, configuration: IntegrationConfiguration
    ) -> IntegrationHealth:
        """Return a synthetic health snapshot (no real probe is performed)."""
        return IntegrationHealth(
            state=HealthState.UNKNOWN,
            message="offline reference provider — no live probe performed",
        )
