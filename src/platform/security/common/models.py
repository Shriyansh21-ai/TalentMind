"""Shared security-platform value types (Module 14 · Module 17).

Small, dependency-light enums reused across identity, authorization, audit,
monitoring, governance, compliance, threat and incident modules — one definition
of each concept rather than a copy per module.
"""

from __future__ import annotations

from enum import Enum


class Decision(str, Enum):
    """The outcome of a policy / authorization evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(str, Enum):
    """A coarse risk rating, ordered by severity."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Return an ordinal where a higher number is riskier."""
        return {
            RiskLevel.NONE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }[self]

    @classmethod
    def highest(cls, levels: list[RiskLevel]) -> RiskLevel:
        """Return the riskiest level in ``levels`` (NONE if empty)."""
        if not levels:
            return cls.NONE
        return max(levels, key=lambda level: level.rank)


class Severity(str, Enum):
    """Severity for alerts, incidents and security events."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Return an ordinal where a higher number is more severe."""
        return {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }[self]
