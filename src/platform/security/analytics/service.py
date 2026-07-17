"""Operational analytics (Module 13).

A read-side aggregation over the security/governance services that produces
security, audit, policy, incident and monitoring metrics plus a simple trend
analysis and an executive operational dashboard. It holds no state of its own —
it composes the other services — so its numbers can never diverge from source.
"""

from __future__ import annotations

from src.platform.security.audit.service import EnterpriseAuditService
from src.platform.security.compliance.service import ComplianceService
from src.platform.security.governance.service import GovernanceService
from src.platform.security.incidents.service import IncidentService
from src.platform.security.monitoring.service import MonitoringService
from src.platform.security.threat.service import ThreatDetectionService


def trend(values: list[float]) -> dict[str, object]:
    """Return a simple trend descriptor for a numeric series."""
    if len(values) < 2:
        return {"direction": "flat", "delta": 0.0, "points": len(values)}
    delta = values[-1] - values[0]
    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {"direction": direction, "delta": delta, "points": len(values)}


class OperationalAnalyticsService:
    """Aggregates operational metrics across the security platform."""

    def __init__(
        self,
        *,
        audit: EnterpriseAuditService | None = None,
        monitoring: MonitoringService | None = None,
        governance: GovernanceService | None = None,
        incidents: IncidentService | None = None,
        threat: ThreatDetectionService | None = None,
        compliance: ComplianceService | None = None,
    ) -> None:
        self._audit = audit
        self._monitoring = monitoring
        self._governance = governance
        self._incidents = incidents
        self._threat = threat
        self._compliance = compliance

    # -- domain metrics -----------------------------------------------------

    def security_metrics(self, tenant_id: str, organization_id: str) -> dict[str, object]:
        """Return threat/security metrics for a tenant."""
        if self._threat is None:
            return {}
        report = self._threat.threat_report(tenant_id, organization_id)
        return {
            "total_events": report.total_events,
            "unresolved": report.unresolved,
            "highest_risk": report.highest_risk.value,
            "by_risk": report.by_risk,
        }

    def audit_metrics(self, tenant_id: str) -> dict[str, object]:
        """Return audit-volume metrics for a tenant."""
        if self._audit is None:
            return {}
        entries = self._audit.search(tenant_id, limit=10_000)
        by_type: dict[str, int] = {}
        for entry in entries:
            by_type[entry.event_type.value] = by_type.get(entry.event_type.value, 0) + 1
        return {
            "total": len(entries),
            "by_type": by_type,
            "chain_intact": self._audit.verify_chain(tenant_id),
        }

    def policy_metrics(self, tenant_id: str) -> dict[str, object]:
        """Return governance-policy metrics for a tenant."""
        if self._governance is None:
            return {}
        policies = self._governance.policies_for(tenant_id)
        return {
            "total_policies": len(policies),
            "enforced": sum(1 for p in policies if p.enforcement.value == "enforce"),
        }

    def incident_metrics(self, tenant_id: str) -> dict[str, object]:
        """Return incident metrics for a tenant."""
        if self._incidents is None:
            return {}
        return self._incidents.report(tenant_id)

    def monitoring_metrics(self, tenant_id: str) -> dict[str, object]:
        """Return alerting metrics for a tenant."""
        if self._monitoring is None:
            return {}
        active = self._monitoring.active_alerts(tenant_id)
        by_severity: dict[str, int] = {}
        for alert in active:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
        return {"active_alerts": len(active), "by_severity": by_severity}

    # -- executive dashboard -----------------------------------------------

    def executive_dashboard(self, tenant_id: str, organization_id: str) -> dict[str, object]:
        """Return a combined executive operational snapshot for a tenant."""
        return {
            "security": self.security_metrics(tenant_id, organization_id),
            "audit": self.audit_metrics(tenant_id),
            "policy": self.policy_metrics(tenant_id),
            "incidents": self.incident_metrics(tenant_id),
            "monitoring": self.monitoring_metrics(tenant_id),
        }
