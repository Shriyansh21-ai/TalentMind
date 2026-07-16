"""Shared foundation for the Enterprise Security & Governance Platform.

The security error hierarchy and shared value types (decisions, risk levels,
severities) reused across identity, authorization, audit, monitoring,
governance, compliance, threat and incident modules.
"""

from __future__ import annotations

from src.platform.security.common.errors import (
    AuthorizationError,
    ComplianceError,
    ConfigurationGovernanceError,
    IdentityError,
    IncidentError,
    PolicyError,
    PolicyViolationError,
    SecretError,
    SecurityPlatformError,
    ThreatError,
)
from src.platform.security.common.models import Decision, RiskLevel, Severity

__all__ = [
    "SecurityPlatformError",
    "IdentityError",
    "AuthorizationError",
    "PolicyError",
    "PolicyViolationError",
    "SecretError",
    "ComplianceError",
    "ThreatError",
    "IncidentError",
    "ConfigurationGovernanceError",
    "Decision",
    "RiskLevel",
    "Severity",
]
