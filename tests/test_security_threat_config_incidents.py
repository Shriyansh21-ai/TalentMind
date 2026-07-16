"""Modules 9, 11 & 12 tests — threat detection, config governance, incidents.

Threat: brute-force, escalation, drift detection, threat report, anomaly
detector. Config: versioning, approval workflow, validation, rollback. Incidents:
lifecycle, escalation, timeline, resolution and reporting.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.security.common.errors import ConfigurationGovernanceError
from src.platform.security.common.models import RiskLevel, Severity
from src.platform.security.configuration import (
    ConfigurationGovernanceService,
    ConfigStatus,
)
from src.platform.security.incidents import IncidentService, IncidentStatus
from src.platform.security.threat import (
    ThreatDetectionService,
    ThreatType,
    ThresholdAnomalyDetector,
)


# -- threat -----------------------------------------------------------------


def test_brute_force_after_threshold():
    svc = ThreatDetectionService(brute_force_threshold=3, clock=FrozenClock())
    assert svc.record_access_attempt("t1", "o1", "m", success=False) is None
    assert svc.record_access_attempt("t1", "o1", "m", success=False) is None
    event = svc.record_access_attempt("t1", "o1", "m", success=False)
    assert event is not None and event.threat_type == ThreatType.BRUTE_FORCE


def test_permission_escalation_detected():
    svc = ThreatDetectionService(clock=FrozenClock())
    event = svc.detect_permission_escalation("t1", "o1", "u", added_roles=["platform_admin"])
    assert event is not None and event.risk_level == RiskLevel.HIGH
    assert svc.detect_permission_escalation("t1", "o1", "u", added_roles=["viewer"]) is None


def test_configuration_drift_detected():
    svc = ThreatDetectionService(clock=FrozenClock())
    assert svc.detect_configuration_drift("t1", "o1", "app", "h1") is None  # baseline
    drift = svc.detect_configuration_drift("t1", "o1", "app", "h2")
    assert drift is not None and drift.threat_type == ThreatType.CONFIGURATION_DRIFT


def test_threat_report_aggregates_highest_risk():
    svc = ThreatDetectionService(brute_force_threshold=1, clock=FrozenClock())
    svc.record_access_attempt("t1", "o1", "m", success=False)  # HIGH
    svc.detect_access_violation("t1", "o1", "g", "billing:read")  # MEDIUM
    report = svc.threat_report("t1", "o1")
    assert report.total_events == 2
    assert report.highest_risk == RiskLevel.HIGH


def test_anomaly_detector_thresholds():
    detector = ThresholdAnomalyDetector(warn=10, high=50, critical=90)
    assert detector.score(5) == RiskLevel.LOW
    assert detector.score(60) == RiskLevel.HIGH
    assert detector.score(95) == RiskLevel.CRITICAL


# -- configuration governance ----------------------------------------------


def test_config_versioning_and_approval():
    svc = ConfigurationGovernanceService(clock=FrozenClock())
    svc.set_initial("t1", "o1", "timeout", 30)
    change = svc.propose_change("t1", "o1", "timeout", 60, requested_by="u")
    entry = svc.approve("t1", change.id, approver="admin")
    assert entry.current_value == 60
    assert len(svc.history("t1", "timeout")) == 2


def test_config_rollback():
    svc = ConfigurationGovernanceService(clock=FrozenClock())
    svc.set_initial("t1", "o1", "timeout", 30)
    change = svc.propose_change("t1", "o1", "timeout", 60, requested_by="u")
    svc.approve("t1", change.id, approver="admin")
    svc.rollback("t1", "timeout", 1)
    entry = svc.get("t1", "timeout")
    assert entry.current_value == 30
    assert entry.status == ConfigStatus.ROLLED_BACK


def test_config_validation_rejects_bad_value():
    svc = ConfigurationGovernanceService(clock=FrozenClock())
    svc.register_validator("timeout", lambda v: isinstance(v, int) and v > 0)
    with pytest.raises(ConfigurationGovernanceError):
        svc.set_initial("t1", "o1", "timeout", -5)


def test_config_auto_apply_without_approval():
    svc = ConfigurationGovernanceService(require_approval=False, clock=FrozenClock())
    svc.set_initial("t1", "o1", "timeout", 30)
    svc.propose_change("t1", "o1", "timeout", 45, requested_by="u")
    assert svc.get("t1", "timeout").current_value == 45


# -- incidents --------------------------------------------------------------


def test_incident_lifecycle_and_timeline():
    svc = IncidentService(clock=FrozenClock())
    incident = svc.open_incident("t1", "o1", "Outage", severity=Severity.MEDIUM, owner="sre")
    svc.set_root_cause("t1", incident.id, "bad deploy")
    svc.resolve("t1", incident.id, resolution="rollback", actor="sre")
    resolved = svc.get("t1", incident.id)
    assert resolved.status == IncidentStatus.RESOLVED
    assert resolved.root_cause == "bad deploy"
    assert resolved.resolution == "rollback"
    assert len(resolved.timeline) >= 3


def test_incident_escalation_raises_severity():
    svc = IncidentService(clock=FrozenClock())
    incident = svc.open_incident("t1", "o1", "Breach", severity=Severity.MEDIUM)
    svc.escalate("t1", incident.id)
    escalated = svc.get("t1", incident.id)
    assert escalated.severity == Severity.HIGH
    assert escalated.escalated


def test_incident_report():
    svc = IncidentService(clock=FrozenClock())
    svc.open_incident("t1", "o1", "A", severity=Severity.HIGH)
    b = svc.open_incident("t1", "o1", "B", severity=Severity.LOW)
    svc.resolve("t1", b.id, resolution="fixed")
    report = svc.report("t1")
    assert report["total"] == 2 and report["open"] == 1
