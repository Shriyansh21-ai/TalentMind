"""Module 9 — Threat Detection Framework.

Risk-rated security events with deterministic detectors (access violations,
permission escalation, configuration drift, brute-force), an anomaly-detector
seam, threat reports and a SIEM export interface. Offline and rule-based.
"""

from __future__ import annotations

from src.platform.security.threat.models import (
    SecurityEvent,
    ThreatReport,
    ThreatType,
)
from src.platform.security.threat.service import (
    AnomalyDetector,
    SiemExporter,
    ThreatDetectionService,
    ThresholdAnomalyDetector,
)

__all__ = [
    "ThreatType",
    "SecurityEvent",
    "ThreatReport",
    "AnomalyDetector",
    "ThresholdAnomalyDetector",
    "SiemExporter",
    "ThreatDetectionService",
]
