"""Module 2 — Worker Framework.

Worker registration, lifecycle, heartbeats, health, horizontal scaling, graceful
shutdown and aggregate metrics via :class:`WorkerPool`. Deterministic and
clock-driven; shaped for a future distributed worker fleet.
"""

from __future__ import annotations

from src.platform.runtime.workers.models import (
    Worker,
    WorkerContext,
    WorkerMetrics,
    WorkerStatus,
)
from src.platform.runtime.workers.pool import WorkerPool

__all__ = [
    "Worker",
    "WorkerContext",
    "WorkerMetrics",
    "WorkerStatus",
    "WorkerPool",
]
