"""Monitoring models (Module 6).

Alert rules (a metric condition + severity within a monitored domain) and the
alerts they raise. Domains span platform, runtime, AI, integration, security,
health and business monitoring so one monitoring service covers the whole
estate. Rules and alerts are tenant-scoped.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import TenantScopedEntity
from src.platform.security.common.models import Severity


class MonitorDomain(str, Enum):
    """The subsystem a monitor watches."""

    PLATFORM = "platform"
    RUNTIME = "runtime"
    AI = "ai"
    INTEGRATION = "integration"
    SECURITY = "security"
    HEALTH = "health"
    BUSINESS = "business"


class Comparison(str, Enum):
    """The comparison an alert condition applies."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NE = "ne"


class AlertCondition(TenantScopedEntity):
    """A threshold condition on a named metric."""

    metric: str
    comparison: Comparison = Comparison.GT
    threshold: float = 0.0

    def is_triggered(self, value: float) -> bool:
        """Return whether ``value`` breaches this condition."""
        c = self.comparison
        if c == Comparison.GT:
            return value > self.threshold
        if c == Comparison.GTE:
            return value >= self.threshold
        if c == Comparison.LT:
            return value < self.threshold
        if c == Comparison.LTE:
            return value <= self.threshold
        if c == Comparison.EQ:
            return value == self.threshold
        return value != self.threshold


class AlertRule(TenantScopedEntity):
    """A monitoring rule: watch a metric and alert when a condition breaches."""

    name: str
    domain: MonitorDomain = MonitorDomain.PLATFORM
    metric: str
    comparison: Comparison = Comparison.GT
    threshold: float = 0.0
    severity: Severity = Severity.MEDIUM
    enabled: bool = True
    description: str = ""

    def triggered_by(self, value: float) -> bool:
        """Return whether ``value`` triggers this rule."""
        condition = AlertCondition(
            id="_c", tenant_id=self.tenant_id, organization_id=self.organization_id,
            metric=self.metric, comparison=self.comparison, threshold=self.threshold,
        )
        return self.enabled and condition.is_triggered(value)


class Alert(TenantScopedEntity):
    """A raised alert instance."""

    rule_id: str
    name: str
    domain: MonitorDomain = MonitorDomain.PLATFORM
    severity: Severity = Severity.MEDIUM
    metric: str = ""
    value: float = 0.0
    threshold: float = 0.0
    message: str = ""
    triggered_at: datetime | None = None
    resolved: bool = False
    resolved_at: datetime | None = None
