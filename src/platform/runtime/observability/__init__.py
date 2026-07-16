"""Module 13 — Observability Runtime.

Structured runtime logs and latency/execution metrics with an
OpenTelemetry-ready tracing seam. In-memory and offline — no vendor integration.
"""

from __future__ import annotations

from src.platform.runtime.observability.telemetry import (
    ExecutionCounter,
    LatencyStats,
    NoOpTracer,
    RuntimeLogEntry,
    RuntimeTelemetry,
    Span,
    Tracer,
)

__all__ = [
    "RuntimeTelemetry",
    "RuntimeLogEntry",
    "LatencyStats",
    "ExecutionCounter",
    "Tracer",
    "Span",
    "NoOpTracer",
]
