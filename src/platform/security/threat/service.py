"""Threat detection service (Module 9).

Records risk-rated security events and ships deterministic detectors for access
violations, permission escalation, configuration drift and brute-force /
suspicious activity, plus an anomaly-detector seam. Aggregates a tenant's
posture into a :class:`ThreatReport` and exposes a SIEM export interface. All
detection is rule-based and offline — no ML, no network.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import Metadata
from src.platform.common.repository import InMemoryRepository
from src.platform.security.common.models import RiskLevel
from src.platform.security.threat.models import (
    SecurityEvent,
    ThreatReport,
    ThreatType,
)


@runtime_checkable
class AnomalyDetector(Protocol):
    """Scores an observation into a risk level (interface only)."""

    def score(self, value: float) -> RiskLevel: ...


class ThresholdAnomalyDetector:
    """A deterministic anomaly detector: risk grows past configured thresholds."""

    def __init__(self, *, warn: float, high: float, critical: float) -> None:
        self._warn = warn
        self._high = high
        self._critical = critical

    def score(self, value: float) -> RiskLevel:
        """Return the risk level implied by ``value``."""
        if value >= self._critical:
            return RiskLevel.CRITICAL
        if value >= self._high:
            return RiskLevel.HIGH
        if value >= self._warn:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


@runtime_checkable
class SiemExporter(Protocol):
    """A SIEM export seam (interface only — future Splunk/Sentinel/etc.)."""

    name: str

    def export(self, events: list[SecurityEvent]) -> None: ...


class ThreatDetectionService:
    """Records, detects and reports security threats (tenant-isolated)."""

    def __init__(
        self,
        *,
        brute_force_threshold: int = 5,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._brute_force_threshold = brute_force_threshold
        self.events: InMemoryRepository[SecurityEvent] = InMemoryRepository("security_event")
        # (tenant, actor) -> failed attempt count
        self._failed_access: dict[tuple[str, str], int] = {}
        # (tenant, key) -> last known config hash (for drift)
        self._config_baseline: dict[tuple[str, str], str] = {}

    # -- recording ----------------------------------------------------------

    def report_event(
        self,
        tenant_id: str,
        organization_id: str,
        threat_type: ThreatType,
        *,
        risk_level: RiskLevel = RiskLevel.LOW,
        actor_id: str = "",
        source: str = "",
        description: str = "",
        metadata: dict[str, object] | None = None,
    ) -> SecurityEvent:
        """Record a security event for a tenant."""
        now = self._clock.now()
        event = SecurityEvent(
            id=generate_id("sev"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            threat_type=threat_type,
            risk_level=risk_level,
            actor_id=actor_id,
            source=source,
            description=description,
            detected_at=now,
            metadata=Metadata(values=metadata or {}),
            created_at=now,
            updated_at=now,
        )
        return self.events.add(event)

    # -- deterministic detectors -------------------------------------------

    def record_access_attempt(
        self, tenant_id: str, organization_id: str, actor_id: str, *, success: bool
    ) -> SecurityEvent | None:
        """Track access attempts; raise a brute-force event past the threshold."""
        key = (tenant_id, actor_id)
        if success:
            self._failed_access.pop(key, None)
            return None
        count = self._failed_access.get(key, 0) + 1
        self._failed_access[key] = count
        if count >= self._brute_force_threshold:
            return self.report_event(
                tenant_id,
                organization_id,
                ThreatType.BRUTE_FORCE,
                risk_level=RiskLevel.HIGH,
                actor_id=actor_id,
                description=f"{count} consecutive failed access attempts",
                metadata={"attempts": count},
            )
        return None

    def detect_access_violation(
        self, tenant_id: str, organization_id: str, actor_id: str, permission: str
    ) -> SecurityEvent:
        """Record an access-violation event (denied permission)."""
        return self.report_event(
            tenant_id,
            organization_id,
            ThreatType.ACCESS_VIOLATION,
            risk_level=RiskLevel.MEDIUM,
            actor_id=actor_id,
            description=f"denied access to '{permission}'",
            metadata={"permission": permission},
        )

    def detect_permission_escalation(
        self,
        tenant_id: str,
        organization_id: str,
        actor_id: str,
        *,
        added_roles: list[str],
        privileged: list[str] | None = None,
    ) -> SecurityEvent | None:
        """Flag escalation when a privileged role is granted."""
        privileged_set = set(privileged or ["platform_admin", "organization_admin"])
        gained = [r for r in added_roles if r in privileged_set]
        if not gained:
            return None
        return self.report_event(
            tenant_id,
            organization_id,
            ThreatType.PERMISSION_ESCALATION,
            risk_level=RiskLevel.HIGH,
            actor_id=actor_id,
            description=f"privileged roles granted: {gained}",
            metadata={"roles": gained},
        )

    def detect_configuration_drift(
        self, tenant_id: str, organization_id: str, config_key: str, config_hash: str
    ) -> SecurityEvent | None:
        """Flag drift when a config hash differs from its recorded baseline."""
        key = (tenant_id, config_key)
        baseline = self._config_baseline.get(key)
        self._config_baseline[key] = config_hash
        if baseline is not None and baseline != config_hash:
            return self.report_event(
                tenant_id,
                organization_id,
                ThreatType.CONFIGURATION_DRIFT,
                risk_level=RiskLevel.MEDIUM,
                description=f"configuration '{config_key}' drifted from baseline",
                metadata={"config_key": config_key},
            )
        return None

    # -- queries ------------------------------------------------------------

    def resolve(self, tenant_id: str, event_id: str) -> SecurityEvent:
        """Mark a security event resolved."""
        event = self.events.require(event_id, tenant_id=tenant_id)
        event.resolved = True
        event.touch(self._clock.now())
        return self.events.update(event)

    def list_events(self, tenant_id: str, *, unresolved_only: bool = False) -> list[SecurityEvent]:
        """Return a tenant's security events."""
        where = (lambda e: not e.resolved) if unresolved_only else None
        return self.events.list(tenant_id=tenant_id, where=where)

    def threat_report(self, tenant_id: str, organization_id: str) -> ThreatReport:
        """Aggregate a tenant's threat posture into a report."""
        events = self.list_events(tenant_id)
        by_type: dict[str, int] = {}
        by_risk: dict[str, int] = {}
        for event in events:
            by_type[event.threat_type.value] = by_type.get(event.threat_type.value, 0) + 1
            by_risk[event.risk_level.value] = by_risk.get(event.risk_level.value, 0) + 1
        now = self._clock.now()
        return ThreatReport(
            id=generate_id("thrept"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            total_events=len(events),
            unresolved=sum(1 for e in events if not e.resolved),
            highest_risk=RiskLevel.highest([e.risk_level for e in events]),
            by_type=by_type,
            by_risk=by_risk,
            created_at=now,
            updated_at=now,
        )
