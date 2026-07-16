"""Module 6 — Monitoring Platform.

Alert rules and conditions across platform / runtime / AI / integration /
security / health / business domains, evaluated by :class:`MonitoringService`
which raises tenant-scoped alerts with severities and fires notification hooks.
"""

from __future__ import annotations

from src.platform.security.monitoring.models import (
    Alert,
    AlertCondition,
    AlertRule,
    Comparison,
    MonitorDomain,
)
from src.platform.security.monitoring.service import (
    MonitoringService,
    NotificationHook,
)

__all__ = [
    "MonitorDomain",
    "Comparison",
    "AlertCondition",
    "AlertRule",
    "Alert",
    "MonitoringService",
    "NotificationHook",
]
