"""Module 9 — Resource Management.

CPU/memory/disk (via optional psutil, interfaces-only otherwise) plus
application metrics (queue/worker/AI/connection), platform utilization and a
capacity planner. Decoupled via injected application-metric getters.
"""

from __future__ import annotations

from src.platform.runtime.resources.metrics import (
    ApplicationMetrics,
    CapacityPlan,
    MetricsProvider,
    NullMetricsProvider,
    PlatformUtilization,
    PsutilMetricsProvider,
    ResourceMonitor,
    SystemMetrics,
    default_metrics_provider,
)

__all__ = [
    "SystemMetrics",
    "ApplicationMetrics",
    "PlatformUtilization",
    "CapacityPlan",
    "MetricsProvider",
    "NullMetricsProvider",
    "PsutilMetricsProvider",
    "default_metrics_provider",
    "ResourceMonitor",
]
