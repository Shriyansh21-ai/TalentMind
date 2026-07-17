"""Platform composition root (Modules 14 & 18).

Wires every module's service together into one lazily-constructed
:class:`Platform` facade using the :class:`~src.platform.container.Container`.
Services share a single injected :class:`Clock` and the appropriate shared
repositories (e.g. tenancy and organizations share an org repository), so the
object graph is consistent and built at most once (lazy singletons).

:meth:`Platform.provision_organization` demonstrates safe cross-module
integration: it creates an organization, provisions its tenant, seeds a
subscription + configuration, and writes an audit event — all additive, none of
it touching the Phase 1-5 engines.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.audit import AuditCategory, PlatformAuditService
from src.platform.auth import AuthenticationManager
from src.platform.common.clock import Clock, SystemClock
from src.platform.config import ConfigurationService
from src.platform.container import Container
from src.platform.deployment.bootstrap import (
    DeploymentPlatform,
    build_deployment_platform,
)
from src.platform.developer import ExtensionRegistry
from src.platform.integrations.bootstrap import (
    IntegrationPlatform,
    build_integration_platform,
)
from src.platform.notifications import NotificationService
from src.platform.organizations import Organization, OrganizationService
from src.platform.rbac import AccessControlService
from src.platform.runtime.bootstrap import RuntimePlatform, build_runtime_platform
from src.platform.security.bootstrap import (
    SecurityPlatform,
    build_security_platform,
)
from src.platform.storage import StorageService
from src.platform.subscription import PlanTier, SubscriptionService
from src.platform.tenancy import Tenant, TenantService


@dataclass
class Platform:
    """A fully-wired platform instance exposing every module's service."""

    container: Container
    clock: Clock

    # -- service accessors (lazy via the container) -------------------------

    @property
    def organizations(self) -> OrganizationService:
        return self.container.resolve("organizations")  # type: ignore[return-value]

    @property
    def tenants(self) -> TenantService:
        return self.container.resolve("tenants")  # type: ignore[return-value]

    @property
    def auth(self) -> AuthenticationManager:
        return self.container.resolve("auth")  # type: ignore[return-value]

    @property
    def access_control(self) -> AccessControlService:
        return self.container.resolve("rbac")  # type: ignore[return-value]

    @property
    def workspaces(self):
        return self.container.resolve("workspaces")

    @property
    def config(self) -> ConfigurationService:
        return self.container.resolve("config")  # type: ignore[return-value]

    @property
    def subscriptions(self) -> SubscriptionService:
        return self.container.resolve("subscriptions")  # type: ignore[return-value]

    @property
    def notifications(self) -> NotificationService:
        return self.container.resolve("notifications")  # type: ignore[return-value]

    @property
    def audit(self) -> PlatformAuditService:
        return self.container.resolve("audit")  # type: ignore[return-value]

    @property
    def storage(self) -> StorageService:
        return self.container.resolve("storage")  # type: ignore[return-value]

    @property
    def extensions(self) -> ExtensionRegistry:
        return self.container.resolve("extensions")  # type: ignore[return-value]

    @property
    def integrations(self) -> IntegrationPlatform:
        """The Enterprise Integration Platform (Phase 6 / Milestone 2)."""
        return self.container.resolve("integrations")  # type: ignore[return-value]

    @property
    def runtime(self) -> RuntimePlatform:
        """The Enterprise Runtime Platform (Phase 6 / Milestone 3)."""
        return self.container.resolve("runtime")  # type: ignore[return-value]

    @property
    def security(self) -> SecurityPlatform:
        """The Enterprise Security & Governance Platform (Phase 6 / Milestone 4)."""
        return self.container.resolve("security")  # type: ignore[return-value]

    @property
    def deployment(self) -> DeploymentPlatform:
        """The Enterprise Deployment Platform (Phase 6 / Milestone 5)."""
        return self.container.resolve("deployment")  # type: ignore[return-value]

    # -- high-level integration --------------------------------------------

    def provision_organization(
        self,
        legal_name: str,
        *,
        slug: str | None = None,
        plan: PlanTier = PlanTier.FREE,
    ) -> tuple[Organization, Tenant]:
        """Provision a complete, ready-to-use organization + tenant.

        Creates the organization, provisions its tenant, seeds a subscription
        and configuration, and records an audit event. Returns the pair.
        """
        org = self.organizations.create_organization(legal_name, slug=slug)
        tenant = self.tenants.provision(org)
        self.subscriptions.subscribe(org.id, org.id, plan)
        self.config.ensure(org.id, org.id)
        self.audit.record(
            org.id,
            org.id,
            AuditCategory.ORGANIZATION,
            "organization.provisioned",
            target_type="organization",
            target_id=org.id,
            metadata={"plan": plan.value, "slug": org.slug},
        )
        return org, tenant


def build_platform(*, clock: Clock | None = None) -> Platform:
    """Compose and return a fully-wired :class:`Platform` (lazy singletons)."""
    the_clock = clock or SystemClock()
    container = Container()

    # Organizations own the org repository; tenancy shares it (1:1 mapping).
    container.register("organizations", lambda _c: OrganizationService(clock=the_clock))
    container.register(
        "tenants",
        lambda c: TenantService(
            c.resolve("organizations").repo,
            clock=the_clock,  # type: ignore[union-attr]
        ),
    )
    container.register("auth", lambda _c: AuthenticationManager(clock=the_clock))
    container.register("rbac", lambda _c: AccessControlService(clock=the_clock))

    # Local import avoids a heavy import at module load; workspaces is optional.
    def _workspaces(_c):
        from src.platform.workspaces import WorkspaceService

        return WorkspaceService(clock=the_clock)

    container.register("workspaces", _workspaces)
    container.register("config", lambda _c: ConfigurationService(clock=the_clock))
    container.register("subscriptions", lambda _c: SubscriptionService(clock=the_clock))
    container.register("notifications", lambda _c: NotificationService(clock=the_clock))
    container.register("audit", lambda _c: PlatformAuditService(clock=the_clock))
    container.register("storage", lambda _c: StorageService(clock=the_clock))
    container.register("extensions", lambda _c: ExtensionRegistry())
    # Phase 6 / Milestone 2 — the Enterprise Integration Platform is wired as a
    # lazily-built sub-platform, sharing the same injected clock.
    container.register("integrations", lambda _c: build_integration_platform(clock=the_clock))
    # Phase 6 / Milestone 3 — the Enterprise Runtime Platform shares the same
    # injected clock and publishes runtime events onto the integration platform's
    # enterprise event bus (Module 12 — integrate with the existing event bus).
    container.register(
        "runtime",
        lambda c: build_runtime_platform(
            clock=the_clock,
            event_bus=c.resolve("integrations").events,  # type: ignore[union-attr]
        ),
    )
    # Phase 6 / Milestone 4 — the Enterprise Security & Governance Platform,
    # additive and sharing the same injected clock.
    container.register("security", lambda _c: build_security_platform(clock=the_clock))
    # Phase 6 / Milestone 5 — the Enterprise Deployment Platform, additive and
    # sharing the same injected clock.
    container.register("deployment", lambda _c: build_deployment_platform(clock=the_clock))

    return Platform(container=container, clock=the_clock)
