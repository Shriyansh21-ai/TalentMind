"""Security-platform exception hierarchy (Phase 6 / Milestone 4).

Extends the platform-wide :class:`~src.platform.common.errors.PlatformError`
hierarchy with errors specific to the Enterprise Security, Governance,
Compliance and Observability platform. No business-logic exceptions live here —
only security/governance concerns (identity, authorization, secrets, policy,
compliance, threats, incidents).
"""

from __future__ import annotations

from src.platform.common.errors import PlatformError


class SecurityPlatformError(PlatformError):
    """Base class for every enterprise-security-platform error."""

    code = "security_error"


class IdentityError(SecurityPlatformError):
    """Raised on an invalid identity operation or unknown identity."""

    code = "identity_error"


class AuthorizationError(SecurityPlatformError):
    """Raised when an authorization decision denies an action."""

    code = "authorization_denied"


class PolicyError(SecurityPlatformError):
    """Raised on an invalid policy definition or evaluation error."""

    code = "policy_error"


class PolicyViolationError(SecurityPlatformError):
    """Raised when an operation violates an enforced governance policy."""

    code = "policy_violation"


class SecretError(SecurityPlatformError):
    """Raised when a secret is missing, expired or accessed unsafely."""

    code = "secret_error"


class ComplianceError(SecurityPlatformError):
    """Raised on a compliance-framework misuse."""

    code = "compliance_error"


class ThreatError(SecurityPlatformError):
    """Raised on a threat-detection misuse."""

    code = "threat_error"


class IncidentError(SecurityPlatformError):
    """Raised on an invalid incident-management operation."""

    code = "incident_error"


class ConfigurationGovernanceError(SecurityPlatformError):
    """Raised on an invalid configuration-governance operation."""

    code = "configuration_governance_error"
