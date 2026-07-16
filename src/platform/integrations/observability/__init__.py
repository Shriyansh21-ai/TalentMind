"""Module 15 — Integration Observability.

Connection statistics, failure/retry tracking, latency metrics and a bounded
structured-log ring for the integration platform. In-memory and offline; a
production deployment binds these hooks to a real metrics/logging backend.
"""

from __future__ import annotations

from src.platform.integrations.observability.metrics import (
    ConnectionStatistics,
    IntegrationLogEntry,
    LogLevel,
    ObservabilityRegistry,
)

__all__ = [
    "ConnectionStatistics",
    "IntegrationLogEntry",
    "LogLevel",
    "ObservabilityRegistry",
]
