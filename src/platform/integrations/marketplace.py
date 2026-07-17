"""Integration Marketplace service (Module 11).

Aggregates the read-side of the integration platform into view models the
Marketplace workspace renders: the available-provider catalogue, a tenant's
installed integrations, per-integration health/capabilities/logs and sync/webhook
status. It is a thin composition over the manager, sync, webhook and
observability services — it holds no state of its own and enforces no new rules,
so it can never diverge from the source of truth.
"""

from __future__ import annotations

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.integrations.common.models import (
    Integration,
    IntegrationDefinition,
    ProviderCategory,
)
from src.platform.integrations.manager import IntegrationManager
from src.platform.integrations.observability import (
    ConnectionStatistics,
    IntegrationLogEntry,
    ObservabilityRegistry,
)
from src.platform.integrations.sync.service import SynchronizationService
from src.platform.integrations.webhooks.service import WebhookService


class MarketplaceOverview(PlatformModel):
    """Top-line marketplace counters for a tenant."""

    available_providers: int = 0
    installed: int = 0
    connected: int = 0
    healthy: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)


class IntegrationDetail(PlatformModel):
    """Everything the marketplace shows for one installed integration."""

    integration: Integration
    definition: IntegrationDefinition
    statistics: ConnectionStatistics | None = None
    logs: list[IntegrationLogEntry] = Field(default_factory=list)
    sync_health: dict[str, object] = Field(default_factory=dict)
    webhook_subscriptions: int = 0


class MarketplaceService:
    """Read-side aggregation for the Integration Marketplace workspace."""

    def __init__(
        self,
        manager: IntegrationManager,
        *,
        sync: SynchronizationService | None = None,
        webhooks: WebhookService | None = None,
        observability: ObservabilityRegistry | None = None,
    ) -> None:
        self._manager = manager
        self._sync = sync
        self._webhooks = webhooks
        self._observability = observability or manager.observability

    # -- catalogue ----------------------------------------------------------

    def catalog(self, *, category: ProviderCategory | None = None) -> list[IntegrationDefinition]:
        """Return the available-provider catalogue, optionally by category."""
        return self._manager.available_providers(category=category)

    def search(self, term: str) -> list[IntegrationDefinition]:
        """Return catalogue entries whose name/description/tags match ``term``."""
        needle = term.strip().lower()
        if not needle:
            return self.catalog()
        matches = []
        for definition in self.catalog():
            meta = definition.metadata
            haystack = " ".join(
                [meta.display_name, meta.vendor, meta.description, *meta.tags]
            ).lower()
            if needle in haystack:
                matches.append(definition)
        return matches

    # -- installed ----------------------------------------------------------

    def installed(self, tenant_id: str) -> list[Integration]:
        """Return a tenant's installed integrations."""
        return self._manager.list(tenant_id)

    def overview(self, tenant_id: str) -> MarketplaceOverview:
        """Return top-line marketplace counters for a tenant."""
        installed = self.installed(tenant_id)
        by_category: dict[str, int] = {}
        for integration in installed:
            key = integration.category.value
            by_category[key] = by_category.get(key, 0) + 1
        return MarketplaceOverview(
            available_providers=len(self.catalog()),
            installed=len(installed),
            connected=sum(1 for i in installed if i.is_connected),
            healthy=sum(1 for i in installed if i.health.is_healthy),
            by_category=by_category,
        )

    def detail(self, tenant_id: str, integration_id: str) -> IntegrationDetail:
        """Return the full aggregated detail view for one integration."""
        integration = self._manager.get(tenant_id, integration_id)
        definition = self._manager.registry.definition(integration.definition_key)
        statistics = self._observability.stats_for(tenant_id, integration_id)
        logs = self._observability.logs(tenant_id=tenant_id, integration_id=integration_id)
        sync_health: dict[str, object] = {}
        if self._sync is not None:
            sync_health = self._sync.health(tenant_id, integration_id)
        webhook_count = 0
        if self._webhooks is not None:
            webhook_count = len(self._webhooks.subscriptions(tenant_id))
        return IntegrationDetail(
            integration=integration,
            definition=definition,
            statistics=statistics,
            logs=logs,
            sync_health=sync_health,
            webhook_subscriptions=webhook_count,
        )
