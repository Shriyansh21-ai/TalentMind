"""Integration manager (Module 1 — the platform's integration control plane).

The :class:`IntegrationManager` is the single application service for the
lifecycle of installed integrations: discover available providers, install one
for a tenant, (dis)connect it, re-configure it, check its health and uninstall
it. It composes the registry (providers), a tenant-isolated repository (installed
records), a :class:`CredentialVault` (secrets), an
:class:`ObservabilityRegistry` (telemetry) and an optional event publisher.

Every mutating call is tenant-scoped and isolation-checked at the repository
boundary, credentials are stored only as opaque references, and lifecycle
transitions emit both a structured log line and (optionally) a platform event.
"""

from __future__ import annotations

from typing import Callable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.integrations.common.errors import (
    IntegrationNotConnectedError,
)
from src.platform.integrations.common.models import (
    HealthState,
    Integration,
    IntegrationConfiguration,
    IntegrationDefinition,
    IntegrationStatus,
    ProviderCategory,
)
from src.platform.integrations.common.registry import (
    IntegrationRegistry,
    build_default_registry,
)
from src.platform.integrations.common.secrets import (
    CredentialType,
    CredentialVault,
)
from src.platform.integrations.observability import (
    LogLevel,
    ObservabilityRegistry,
)

#: An event publisher: ``(event_name, tenant_id, payload) -> None``.
EventPublisher = Callable[[str, str, dict], None]


class IntegrationManager:
    """Lifecycle control plane for tenant-installed integrations."""

    def __init__(
        self,
        *,
        registry: IntegrationRegistry | None = None,
        repository: InMemoryRepository[Integration] | None = None,
        vault: CredentialVault | None = None,
        observability: ObservabilityRegistry | None = None,
        publisher: EventPublisher | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.registry = registry or build_default_registry()
        self.repo: InMemoryRepository[Integration] = repository or InMemoryRepository(
            "integration"
        )
        self.vault = vault or CredentialVault(clock=self._clock)
        self.observability = observability or ObservabilityRegistry(clock=self._clock)
        self._publisher = publisher

    # -- discovery ----------------------------------------------------------

    def available_providers(
        self, *, category: ProviderCategory | None = None
    ) -> list[IntegrationDefinition]:
        """Return the catalogue of providers available to install."""
        return self.registry.definitions(category=category)

    # -- lifecycle ----------------------------------------------------------

    def install(
        self,
        tenant_id: str,
        organization_id: str,
        definition_key: str,
        *,
        display_name: str | None = None,
        settings: dict[str, object] | None = None,
        credential: str | None = None,
        credential_type: CredentialType = CredentialType.API_KEY,
        enabled_scopes: list[str] | None = None,
        sync_enabled: bool = False,
        webhook_enabled: bool = False,
    ) -> Integration:
        """Install a provider for a tenant (validated, not yet connected).

        Raises:
            ProviderNotFoundError: If ``definition_key`` is unknown.
            ProviderConfigurationError: If the configuration fails validation.
        """
        provider = self.registry.get(definition_key)
        definition = self.registry.definition(definition_key)

        credential_ref = ""
        if credential:
            ref = self.vault.issue(
                tenant_id, credential, credential_type=credential_type
            )
            credential_ref = ref.ref

        configuration = IntegrationConfiguration(
            settings=settings or {},
            credential_ref=credential_ref,
            enabled_scopes=enabled_scopes or [],
            sync_enabled=sync_enabled,
            webhook_enabled=webhook_enabled,
        )
        # Provider-specific validation happens before we persist anything.
        provider.validate_configuration(configuration)

        now = self._clock.now()
        integration = Integration(
            id=generate_id("intg"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            definition_key=definition_key,
            display_name=display_name or definition.metadata.display_name,
            category=definition.category,
            status=IntegrationStatus.NOT_CONNECTED,
            configuration=configuration,
            created_at=now,
            updated_at=now,
        )
        self.repo.add(integration)
        self._log(integration, "integration.installed", provider=definition_key)
        self._emit("integration.installed", integration)
        return integration

    def get(self, tenant_id: str, integration_id: str) -> Integration:
        """Return one installed integration (tenant-isolated)."""
        return self.repo.require(integration_id, tenant_id=tenant_id)

    def list(
        self, tenant_id: str, *, category: ProviderCategory | None = None
    ) -> list[Integration]:
        """Return a tenant's installed integrations, optionally by category."""
        where = None
        if category is not None:
            where = lambda i: i.category == category  # noqa: E731
        return self.repo.list(tenant_id=tenant_id, where=where)

    def configure(
        self,
        tenant_id: str,
        integration_id: str,
        *,
        settings: dict[str, object] | None = None,
        enabled_scopes: list[str] | None = None,
        sync_enabled: bool | None = None,
        webhook_enabled: bool | None = None,
    ) -> Integration:
        """Update an installed integration's configuration (re-validated)."""
        integration = self.get(tenant_id, integration_id)
        provider = self.registry.get(integration.definition_key)
        config = integration.configuration
        if settings is not None:
            config.settings = settings
        if enabled_scopes is not None:
            config.enabled_scopes = enabled_scopes
        if sync_enabled is not None:
            config.sync_enabled = sync_enabled
        if webhook_enabled is not None:
            config.webhook_enabled = webhook_enabled
        provider.validate_configuration(config)
        integration.configuration = config
        integration.touch(self._clock.now())
        self.repo.update(integration)
        self._log(integration, "integration.configured")
        return integration

    def connect(self, tenant_id: str, integration_id: str) -> Integration:
        """Transition an integration to CONNECTED and refresh its health."""
        integration = self.get(tenant_id, integration_id)
        provider = self.registry.get(integration.definition_key)
        now = self._clock.now()
        health = provider.check_health(integration.configuration)
        # Offline reference: a successful (simulated) connect is HEALTHY.
        if health.state == HealthState.UNKNOWN:
            health.state = HealthState.HEALTHY
            health.message = "connected (offline reference)"
        health.checked_at = now
        integration.health = health
        integration.status = (
            IntegrationStatus.CONNECTED
            if health.state == HealthState.HEALTHY
            else IntegrationStatus.DEGRADED
        )
        integration.last_connected_at = now
        integration.touch(now)
        self.repo.update(integration)
        self.observability.record_connect(tenant_id, integration_id, ok=True)
        self._log(integration, "integration.connected")
        self._emit("integration.connected", integration)
        return integration

    def disconnect(self, tenant_id: str, integration_id: str) -> Integration:
        """Transition an integration back to NOT_CONNECTED."""
        integration = self.get(tenant_id, integration_id)
        integration.status = IntegrationStatus.NOT_CONNECTED
        integration.touch(self._clock.now())
        self.repo.update(integration)
        self._log(integration, "integration.disconnected")
        self._emit("integration.disconnected", integration)
        return integration

    def disable(self, tenant_id: str, integration_id: str) -> Integration:
        """Administratively disable an integration."""
        integration = self.get(tenant_id, integration_id)
        integration.status = IntegrationStatus.DISABLED
        integration.touch(self._clock.now())
        self.repo.update(integration)
        self._log(integration, "integration.disabled", level=LogLevel.WARNING)
        return integration

    def check_health(self, tenant_id: str, integration_id: str) -> Integration:
        """Re-probe (simulate) and persist an integration's health."""
        integration = self.get(tenant_id, integration_id)
        provider = self.registry.get(integration.definition_key)
        health = provider.check_health(integration.configuration)
        if health.state == HealthState.UNKNOWN and integration.is_connected:
            health.state = HealthState.HEALTHY
        health.checked_at = self._clock.now()
        integration.health = health
        integration.touch(self._clock.now())
        self.repo.update(integration)
        return integration

    def credential_preview(self, tenant_id: str, integration_id: str) -> str:
        """Return a redacted preview of the integration's credential."""
        integration = self.get(tenant_id, integration_id)
        ref = integration.configuration.credential_ref
        if not ref:
            return "—"
        return self.vault.redacted(tenant_id, ref)

    def require_connected(self, tenant_id: str, integration_id: str) -> Integration:
        """Return an integration, raising if it is not connected."""
        integration = self.get(tenant_id, integration_id)
        if not integration.is_connected:
            raise IntegrationNotConnectedError(
                f"integration '{integration_id}' is not connected "
                f"(status={integration.status.value})"
            )
        return integration

    def uninstall(self, tenant_id: str, integration_id: str) -> None:
        """Remove an integration and revoke its credential."""
        integration = self.get(tenant_id, integration_id)
        ref = integration.configuration.credential_ref
        if ref:
            self.vault.revoke(tenant_id, ref)
        self.repo.delete(integration_id, tenant_id=tenant_id)
        self._log(integration, "integration.uninstalled", level=LogLevel.WARNING)
        self._emit("integration.uninstalled", integration)

    # -- internals ----------------------------------------------------------

    def _log(
        self,
        integration: Integration,
        event: str,
        *,
        level: LogLevel = LogLevel.INFO,
        **fields: object,
    ) -> None:
        self.observability.log(
            integration.tenant_id,
            integration.id,
            event,
            level=level,
            message=integration.display_name,
            fields=fields,
        )

    def _emit(self, event: str, integration: Integration) -> None:
        if self._publisher is None:
            return
        self._publisher(
            event,
            integration.tenant_id,
            {
                "integration_id": integration.id,
                "definition_key": integration.definition_key,
                "status": integration.status.value,
            },
        )
