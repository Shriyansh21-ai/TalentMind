"""Governance models (Module 7).

Governance policies group *rules* (required attribute conditions) within a
domain (AI / runtime / integration / operational / approval / security) at an
enforcement level (enforce / warn / audit). Exceptions can waive a policy for a
bounded time. Rule conditions reuse the ABAC :class:`AttributeCondition` from the
authorization module (no duplication). Policies and exceptions are tenant-scoped.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity
from src.platform.security.authorization.models import AttributeCondition
from src.platform.security.common.models import Decision


class GovernanceDomain(str, Enum):
    """The area a governance policy governs."""

    AI = "ai"
    RUNTIME = "runtime"
    INTEGRATION = "integration"
    OPERATIONAL = "operational"
    APPROVAL = "approval"
    SECURITY = "security"


class Enforcement(str, Enum):
    """How strictly a policy is enforced."""

    ENFORCE = "enforce"  # violations are blocked
    WARN = "warn"  # violations are surfaced but allowed
    AUDIT = "audit"  # violations are only recorded


class GovernanceRule(PlatformModel):
    """A single required condition within a governance policy."""

    key: str
    description: str = ""
    condition: AttributeCondition
    remediation: str = ""


class GovernancePolicy(TenantScopedEntity):
    """A governance policy: required rules within a domain and enforcement level."""

    name: str
    domain: GovernanceDomain = GovernanceDomain.OPERATIONAL
    enforcement: Enforcement = Enforcement.ENFORCE
    rules: list[GovernanceRule] = Field(default_factory=list)
    requires_approval: bool = False
    approvers: list[str] = Field(default_factory=list)
    enabled: bool = True
    description: str = ""


class GovernanceException(TenantScopedEntity):
    """A time-bounded, approved waiver of a policy."""

    policy_id: str
    reason: str = ""
    approved_by: str = ""
    expires_at: datetime | None = None

    def is_active(self, moment: datetime) -> bool:
        """Return whether the exception is currently in force."""
        return self.expires_at is None or moment < self.expires_at


class RuleViolation(PlatformModel):
    """A record of one failed governance rule."""

    rule_key: str
    description: str = ""
    remediation: str = ""


class PolicyReport(PlatformModel):
    """The outcome of evaluating one governance policy."""

    policy_id: str
    name: str
    domain: GovernanceDomain
    enforcement: Enforcement
    decision: Decision = Decision.ALLOW
    compliant: bool = True
    waived: bool = False
    violations: list[RuleViolation] = Field(default_factory=list)
