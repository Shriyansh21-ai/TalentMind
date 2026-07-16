"""Module 6 — Health Monitoring.

A :class:`HealthAggregator` that composes decoupled component health checks
(platform, worker, queue, cache, integration, AI, database) into one
worst-state-wins :class:`HealthReport`, with ready-made check builders.
"""

from __future__ import annotations

from src.platform.runtime.health.aggregator import (
    HealthAggregator,
    HealthCheck,
    cache_check,
    database_check,
    queue_check,
    static_check,
    worker_pool_check,
)
from src.platform.runtime.health.models import ComponentHealth, HealthReport

__all__ = [
    "ComponentHealth",
    "HealthReport",
    "HealthAggregator",
    "HealthCheck",
    "static_check",
    "worker_pool_check",
    "queue_check",
    "cache_check",
    "database_check",
]
