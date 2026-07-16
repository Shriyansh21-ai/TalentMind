"""Module 5 — Observability Platform.

A unified observability service for logs, metrics and distributed traces, tied
together by correlation / request / span / trace ids, with OpenTelemetry /
Prometheus / Grafana export seams (interfaces only).
"""

from __future__ import annotations

from src.platform.security.observability.models import (
    LogLevel,
    LogRecord,
    Metric,
    MetricType,
    Span,
    SpanStatus,
    Trace,
)
from src.platform.security.observability.service import (
    GrafanaExporter,
    ObservabilityService,
    OpenTelemetryExporter,
    PrometheusExporter,
    TelemetryExporter,
)

__all__ = [
    "LogLevel",
    "LogRecord",
    "MetricType",
    "Metric",
    "SpanStatus",
    "Span",
    "Trace",
    "TelemetryExporter",
    "OpenTelemetryExporter",
    "PrometheusExporter",
    "GrafanaExporter",
    "ObservabilityService",
]
