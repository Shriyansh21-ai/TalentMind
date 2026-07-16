"""Security platform composition root (Module 14 · Module 17).

Wires the Enterprise Security, Governance, Compliance and Observability platform
into one lazily-constructed :class:`SecurityPlatform` facade using the shared
:class:`~src.platform.container.Container`. Every service shares a single
injected :class:`Clock`; the operational-analytics service is wired over the
audit, monitoring, governance, incident, threat and compliance services. All
services are lazy singletons built at most once.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.common.clock import Clock, SystemClock
from src.platform.container import Container
from src.platform.security.analytics.service import OperationalAnalyticsService
from src.platform.security.audit.service import EnterpriseAuditService
from src.platform.security.authorization.engine import AuthorizationEngine
from src.platform.security.compliance.service import ComplianceService
from src.platform.security.configuration.service import ConfigurationGovernanceService
from src.platform.security.governance.service import GovernanceService
from src.platform.security.identity.manager import IdentityManager
from src.platform.security.incidents.service import IncidentService
from src.platform.security.monitoring.service import MonitoringService
from src.platform.security.observability.service import ObservabilityService
from src.platform.security.secrets.manager import SecretManager
from src.platform.security.threat.service import ThreatDetectionService


@dataclass
class SecurityPlatform:
    """A fully-wired security platform exposing every module's service."""

    container: Container
    clock: Clock

    @property
    def identity(self) -> IdentityManager:
        return self.container.resolve("sec.identity")  # type: ignore[return-value]

    @property
    def authorization(self) -> AuthorizationEngine:
        return self.container.resolve("sec.authorization")  # type: ignore[return-value]

    @property
    def audit(self) -> EnterpriseAuditService:
        return self.container.resolve("sec.audit")  # type: ignore[return-value]

    @property
    def secrets(self) -> SecretManager:
        return self.container.resolve("sec.secrets")  # type: ignore[return-value]

    @property
    def observability(self) -> ObservabilityService:
        return self.container.resolve("sec.observability")  # type: ignore[return-value]

    @property
    def monitoring(self) -> MonitoringService:
        return self.container.resolve("sec.monitoring")  # type: ignore[return-value]

    @property
    def governance(self) -> GovernanceService:
        return self.container.resolve("sec.governance")  # type: ignore[return-value]

    @property
    def compliance(self) -> ComplianceService:
        return self.container.resolve("sec.compliance")  # type: ignore[return-value]

    @property
    def threat(self) -> ThreatDetectionService:
        return self.container.resolve("sec.threat")  # type: ignore[return-value]

    @property
    def configuration(self) -> ConfigurationGovernanceService:
        return self.container.resolve("sec.configuration")  # type: ignore[return-value]

    @property
    def incidents(self) -> IncidentService:
        return self.container.resolve("sec.incidents")  # type: ignore[return-value]

    @property
    def analytics(self) -> OperationalAnalyticsService:
        return self.container.resolve("sec.analytics")  # type: ignore[return-value]


def build_security_platform(*, clock: Clock | None = None) -> SecurityPlatform:
    """Compose and return a fully-wired :class:`SecurityPlatform`."""
    the_clock = clock or SystemClock()
    container = Container()

    container.register("sec.identity", lambda _c: IdentityManager(clock=the_clock))
    container.register(
        "sec.authorization", lambda _c: AuthorizationEngine(clock=the_clock)
    )
    container.register("sec.audit", lambda _c: EnterpriseAuditService(clock=the_clock))
    container.register("sec.secrets", lambda _c: SecretManager(clock=the_clock))
    container.register(
        "sec.observability", lambda _c: ObservabilityService(clock=the_clock)
    )
    container.register("sec.monitoring", lambda _c: MonitoringService(clock=the_clock))
    container.register("sec.governance", lambda _c: GovernanceService(clock=the_clock))
    container.register("sec.compliance", lambda _c: ComplianceService(clock=the_clock))
    container.register(
        "sec.threat", lambda _c: ThreatDetectionService(clock=the_clock)
    )
    container.register(
        "sec.configuration",
        lambda _c: ConfigurationGovernanceService(clock=the_clock),
    )
    container.register("sec.incidents", lambda _c: IncidentService(clock=the_clock))

    container.register(
        "sec.analytics",
        lambda c: OperationalAnalyticsService(
            audit=c.resolve("sec.audit"),  # type: ignore[arg-type]
            monitoring=c.resolve("sec.monitoring"),  # type: ignore[arg-type]
            governance=c.resolve("sec.governance"),  # type: ignore[arg-type]
            incidents=c.resolve("sec.incidents"),  # type: ignore[arg-type]
            threat=c.resolve("sec.threat"),  # type: ignore[arg-type]
            compliance=c.resolve("sec.compliance"),  # type: ignore[arg-type]
        ),
    )

    return SecurityPlatform(container=container, clock=the_clock)
