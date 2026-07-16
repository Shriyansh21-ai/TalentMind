"""Module 13 — Operational Analytics.

A read-side aggregation producing security, audit, policy, incident and
monitoring metrics, a trend helper, and an executive operational dashboard via
:class:`OperationalAnalyticsService`.
"""

from __future__ import annotations

from src.platform.security.analytics.service import (
    OperationalAnalyticsService,
    trend,
)

__all__ = ["OperationalAnalyticsService", "trend"]
