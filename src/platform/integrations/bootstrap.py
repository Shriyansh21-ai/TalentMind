"""Integration platform composition root (Module 1 · Module 14 · Module 18).

Wires the Enterprise Integration Platform into one lazily-constructed
:class:`IntegrationPlatform` facade using the shared
:class:`~src.platform.container.Container`. Every service shares a single
injected :class:`Clock`, one provider :class:`IntegrationRegistry`, one
:class:`CredentialVault`, one :class:`ObservabilityRegistry` and one
:class:`EnterpriseEventBus`, so the object graph is consistent and built at most
once (lazy singletons).

The manager is wired to publish every lifecycle transition onto the enterprise
event bus, so installing/connecting an integration is observable end-to-end
without any module reaching into another's internals.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.common.clock import Clock, SystemClock
from src.platform.container import Container
from src.platform.integrations.common.registry import (
    IntegrationRegistry,
    build_default_registry,
)
from src.platform.integrations.common.secrets import CredentialVault
from src.platform.integrations.events.bus import EnterpriseEventBus
from src.platform.integrations.events.models import EventType
from src.platform.integrations.gateway.gateway import ApiGateway
from src.platform.integrations.manager import IntegrationManager
from src.platform.integrations.marketplace import MarketplaceService
from src.platform.integrations.observability import ObservabilityRegistry
from src.platform.integrations.sync.service import SynchronizationService
from src.platform.integrations.webhooks.service import WebhookService


@dataclass
class IntegrationPlatform:
    """A fully-wired integration platform exposing every module's service."""

    container: Container
    clock: Clock

    @property
    def registry(self) -> IntegrationRegistry:
        return self.container.resolve("intg.registry")  # type: ignore[return-value]

    @property
    def vault(self) -> CredentialVault:
        return self.container.resolve("intg.vault")  # type: ignore[return-value]

    @property
    def observability(self) -> ObservabilityRegistry:
        return self.container.resolve("intg.observability")  # type: ignore[return-value]

    @property
    def events(self) -> EnterpriseEventBus:
        return self.container.resolve("intg.events")  # type: ignore[return-value]

    @property
    def manager(self) -> IntegrationManager:
        return self.container.resolve("intg.manager")  # type: ignore[return-value]

    @property
    def webhooks(self) -> WebhookService:
        return self.container.resolve("intg.webhooks")  # type: ignore[return-value]

    @property
    def sync(self) -> SynchronizationService:
        return self.container.resolve("intg.sync")  # type: ignore[return-value]

    @property
    def gateway(self) -> ApiGateway:
        return self.container.resolve("intg.gateway")  # type: ignore[return-value]

    @property
    def marketplace(self) -> MarketplaceService:
        return self.container.resolve("intg.marketplace")  # type: ignore[return-value]


def build_integration_platform(
    *,
    clock: Clock | None = None,
    registry: IntegrationRegistry | None = None,
) -> IntegrationPlatform:
    """Compose and return a fully-wired :class:`IntegrationPlatform`."""
    the_clock = clock or SystemClock()
    container = Container()

    container.register("intg.registry", lambda _c: registry or build_default_registry())
    container.register("intg.vault", lambda _c: CredentialVault(clock=the_clock))
    container.register("intg.observability", lambda _c: ObservabilityRegistry(clock=the_clock))
    container.register("intg.events", lambda _c: EnterpriseEventBus(clock=the_clock))

    def _manager(c: Container) -> IntegrationManager:
        events: EnterpriseEventBus = c.resolve("intg.events")  # type: ignore[assignment]

        def publisher(name: str, tenant_id: str, payload: dict) -> None:
            events.publish(
                name,
                payload=payload,
                event_type=EventType.INTEGRATION,
                tenant_id=tenant_id,
            )

        return IntegrationManager(
            registry=c.resolve("intg.registry"),  # type: ignore[arg-type]
            vault=c.resolve("intg.vault"),  # type: ignore[arg-type]
            observability=c.resolve("intg.observability"),  # type: ignore[arg-type]
            publisher=publisher,
            clock=the_clock,
        )

    container.register("intg.manager", _manager)
    container.register(
        "intg.webhooks",
        lambda c: WebhookService(vault=c.resolve("intg.vault"), clock=the_clock),  # type: ignore[arg-type]
    )
    container.register("intg.sync", lambda _c: SynchronizationService(clock=the_clock))
    container.register("intg.gateway", lambda _c: ApiGateway(clock=the_clock))
    container.register(
        "intg.marketplace",
        lambda c: MarketplaceService(
            c.resolve("intg.manager"),  # type: ignore[arg-type]
            sync=c.resolve("intg.sync"),  # type: ignore[arg-type]
            webhooks=c.resolve("intg.webhooks"),  # type: ignore[arg-type]
            observability=c.resolve("intg.observability"),  # type: ignore[arg-type]
        ),
    )

    return IntegrationPlatform(container=container, clock=the_clock)
