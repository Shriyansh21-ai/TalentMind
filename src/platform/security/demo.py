"""Offline demo fixture for the Security & Operations Center (Module 10).

Builds a fully-wired :class:`SecurityPlatform` and drives a deterministic
scenario — identities and a role hierarchy, ABAC policies, audit entries across
domains, secrets, monitoring alerts, governance policies, compliance evidence,
threat events, config changes and incidents — so the operations dashboard and
its AppTest render instantly with realistic data and no network. A
:class:`FrozenClock` makes everything reproducible.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.security.audit.models import AuditEventType
from src.platform.security.authorization.models import (
    AttributeCondition,
    AttributeOperator,
    PolicyEffect,
)
from src.platform.security.bootstrap import SecurityPlatform, build_security_platform
from src.platform.security.common.models import Severity
from src.platform.security.compliance.models import ComplianceStandard
from src.platform.security.governance.models import (
    Enforcement,
    GovernanceDomain,
    GovernanceRule,
)
from src.platform.security.monitoring.models import Comparison, MonitorDomain

_TENANT = "org_acme"
_ORG = "org_acme"


def build_security_demo() -> SecurityPlatform:
    """Return a :class:`SecurityPlatform` driven through a deterministic scenario."""
    sp = build_security_platform(clock=FrozenClock())

    # -- identity + authorization --
    sp.identity.register_identity(
        _TENANT, _ORG, "admin", secret="Adm1n!!secret", roles=["organization_admin"],
        email="admin@acme.com",
    )
    sp.identity.register_identity(
        _TENANT, _ORG, "recruiter", secret="Recr!!secret", roles=["recruiter"],
        email="recruiter@acme.com",
    )
    sp.authorization.hierarchy.define_group(
        _TENANT, _ORG, "recruiting", ["candidate:read", "candidate:update"]
    )
    sp.authorization.hierarchy.define_role(_TENANT, _ORG, "recruiter", groups=["recruiting"])
    sp.authorization.add_policy(
        _TENANT, _ORG, "no-offhours-writes", effect=PolicyEffect.DENY,
        resource="candidate", action="update",
        conditions=[AttributeCondition(
            attribute="environment.after_hours", operator=AttributeOperator.EQ, value=True
        )],
        priority=10,
    )

    # -- audit across domains --
    for event_type, action in [
        (AuditEventType.AUTHENTICATION, "user.login"),
        (AuditEventType.AUTHORIZATION, "access.granted"),
        (AuditEventType.SECURITY, "policy.updated"),
        (AuditEventType.CONFIGURATION, "config.changed"),
        (AuditEventType.INTEGRATION, "connector.synced"),
    ]:
        sp.audit.record(_TENANT, _ORG, event_type, action, actor_id="admin")

    # -- secrets --
    sp.secrets.store(_TENANT, _ORG, "smtp_password", "smtp-secret-9999", rotation_interval_days=30)

    # -- monitoring --
    sp.monitoring.add_rule(
        _TENANT, _ORG, "High error rate", "error_rate",
        domain=MonitorDomain.RUNTIME, comparison=Comparison.GT, threshold=0.05,
        severity=Severity.HIGH,
    )
    sp.monitoring.evaluate(_TENANT, _ORG, {"error_rate": 0.12})

    # -- governance --
    sp.governance.register_policy(
        _TENANT, _ORG, "MFA required", domain=GovernanceDomain.SECURITY,
        enforcement=Enforcement.ENFORCE,
        rules=[GovernanceRule(
            key="mfa", description="MFA must be enabled",
            condition=AttributeCondition(
                attribute="identity.mfa", operator=AttributeOperator.EQ, value=True
            ),
        )],
    )

    # -- compliance --
    for standard in [ComplianceStandard.SOC2, ComplianceStandard.GDPR]:
        for control in sp.compliance.controls(standard)[:3]:
            sp.compliance.collect_evidence(
                _TENANT, _ORG, standard, control.code, description="policy doc", source="platform"
            )
            sp.compliance.collect_evidence(
                _TENANT, _ORG, standard, control.code, description="audit log", source="audit"
            )

    # -- threat events --
    for _ in range(5):
        sp.threat.record_access_attempt(_TENANT, _ORG, "mallory", success=False)
    sp.threat.detect_access_violation(_TENANT, _ORG, "guest", "billing:read")

    # -- configuration governance --
    sp.configuration.set_initial(_TENANT, _ORG, "session_timeout_minutes", 30)
    change = sp.configuration.propose_change(
        _TENANT, _ORG, "session_timeout_minutes", 15, requested_by="admin"
    )
    sp.configuration.approve(_TENANT, change.id, approver="ciso")

    # -- incidents --
    incident = sp.incidents.open_incident(
        _TENANT, _ORG, "Suspicious login burst", severity=Severity.HIGH, owner="soc-analyst"
    )
    sp.incidents.set_root_cause(_TENANT, incident.id, "credential stuffing attempt")
    sp.incidents.resolve(_TENANT, incident.id, resolution="blocked source IPs", actor="soc-analyst")
    sp.incidents.open_incident(
        _TENANT, _ORG, "Cache degradation", severity=Severity.MEDIUM, owner="sre"
    )

    return sp
