"""Module 8 — Compliance Framework.

Representative control catalogues for GDPR, SOC 2, ISO 27001, HIPAA, PCI-DSS and
AI-governance readiness, with tenant evidence collection, coverage assessment,
compliance reports and gap analysis via :class:`ComplianceService`. Framework
only — no legal advice.
"""

from __future__ import annotations

from src.platform.security.compliance.models import (
    ComplianceControl,
    ComplianceReport,
    ComplianceStandard,
    ControlStatus,
    Evidence,
    GapAnalysis,
)
from src.platform.security.compliance.service import ComplianceService

__all__ = [
    "ComplianceStandard",
    "ControlStatus",
    "ComplianceControl",
    "Evidence",
    "ComplianceReport",
    "GapAnalysis",
    "ComplianceService",
]
