"""Threat detection models (Module 9).

Security events (typed, risk-rated), the anomaly-detector seam, and the threat
report aggregating a tenant's events. Deterministic and offline; the shape is
chosen for future SIEM export (each event serialises to a flat record).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import Metadata, TenantScopedEntity
from src.platform.security.common.models import RiskLevel


class ThreatType(str, Enum):
    """The category of a detected security event."""

    ACCESS_VIOLATION = "access_violation"
    PERMISSION_ESCALATION = "permission_escalation"
    CONFIGURATION_DRIFT = "configuration_drift"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE = "brute_force"
    ANOMALY = "anomaly"


class SecurityEvent(TenantScopedEntity):
    """A single, risk-rated security event."""

    threat_type: ThreatType = ThreatType.SUSPICIOUS_ACTIVITY
    risk_level: RiskLevel = RiskLevel.LOW
    actor_id: str = ""
    source: str = ""
    description: str = ""
    detected_at: datetime | None = None
    resolved: bool = False
    metadata: Metadata = Field(default_factory=Metadata)


class ThreatReport(TenantScopedEntity):
    """An aggregated view of a tenant's threat posture."""

    total_events: int = 0
    unresolved: int = 0
    highest_risk: RiskLevel = RiskLevel.NONE
    by_type: dict[str, int] = Field(default_factory=dict)
    by_risk: dict[str, int] = Field(default_factory=dict)
