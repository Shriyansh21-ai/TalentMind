"""Monitoring service (Module 6).

Registers alert rules across monitored domains, evaluates them against a bag of
metric values, raises tenant-scoped alerts and fires registered notification
hooks. Deterministic and clock-driven; notification delivery is an injectable
hook so the platform stays offline by default.
"""

from __future__ import annotations

from collections.abc import Callable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.common.models import Severity
from src.platform.security.monitoring.models import (
    Alert,
    AlertRule,
    Comparison,
    MonitorDomain,
)

#: A notification hook receives a raised alert; return value is ignored.
NotificationHook = Callable[[Alert], None]


class MonitoringService:
    """Rule registration, evaluation, alerting and notification hooks."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self.rules: InMemoryRepository[AlertRule] = InMemoryRepository("alert_rule")
        self.alerts: InMemoryRepository[Alert] = InMemoryRepository("alert")
        self._hooks: list[NotificationHook] = []

    # -- configuration ------------------------------------------------------

    def add_rule(
        self,
        tenant_id: str,
        organization_id: str,
        name: str,
        metric: str,
        *,
        domain: MonitorDomain = MonitorDomain.PLATFORM,
        comparison: Comparison = Comparison.GT,
        threshold: float = 0.0,
        severity: Severity = Severity.MEDIUM,
        description: str = "",
    ) -> AlertRule:
        """Register an alert rule for a tenant."""
        now = self._clock.now()
        rule = AlertRule(
            id=generate_id("rule"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            domain=domain,
            metric=metric,
            comparison=comparison,
            threshold=threshold,
            severity=severity,
            description=description,
            created_at=now,
            updated_at=now,
        )
        return self.rules.add(rule)

    def add_notification_hook(self, hook: NotificationHook) -> None:
        """Register a notification hook fired whenever an alert is raised."""
        self._hooks.append(hook)

    # -- evaluation ---------------------------------------------------------

    def evaluate(
        self, tenant_id: str, organization_id: str, metrics: dict[str, float]
    ) -> list[Alert]:
        """Evaluate every enabled rule against ``metrics``; raise alerts."""
        raised: list[Alert] = []
        now = self._clock.now()
        for rule in self.rules.list(tenant_id=tenant_id):
            if rule.metric not in metrics:
                continue
            value = metrics[rule.metric]
            if not rule.triggered_by(value):
                continue
            alert = Alert(
                id=generate_id("alert"),
                tenant_id=tenant_id,
                organization_id=organization_id,
                rule_id=rule.id,
                name=rule.name,
                domain=rule.domain,
                severity=rule.severity,
                metric=rule.metric,
                value=value,
                threshold=rule.threshold,
                message=f"{rule.name}: {rule.metric}={value} breached {rule.comparison.value} {rule.threshold}",
                triggered_at=now,
                created_at=now,
                updated_at=now,
            )
            self.alerts.add(alert)
            raised.append(alert)
            for hook in self._hooks:
                try:
                    hook(alert)
                except Exception:  # isolation — a bad hook never breaks alerting
                    continue
        return raised

    # -- queries ------------------------------------------------------------

    def resolve(self, tenant_id: str, alert_id: str) -> Alert:
        """Mark an alert resolved."""
        alert = self.alerts.require(alert_id, tenant_id=tenant_id)
        alert.resolved = True
        alert.resolved_at = self._clock.now()
        alert.touch(alert.resolved_at)
        return self.alerts.update(alert)

    def active_alerts(self, tenant_id: str, *, domain: MonitorDomain | None = None) -> list[Alert]:
        """Return unresolved alerts, optionally filtered by domain."""

        def _pred(a: Alert) -> bool:
            if a.resolved:
                return False
            return domain is None or a.domain == domain

        return self.alerts.list(tenant_id=tenant_id, where=_pred)

    def all_alerts(self, tenant_id: str) -> list[Alert]:
        """Return every alert for a tenant."""
        return self.alerts.list(tenant_id=tenant_id)

    def rules_for(self, tenant_id: str) -> list[AlertRule]:
        """Return a tenant's alert rules."""
        return self.rules.list(tenant_id=tenant_id)
