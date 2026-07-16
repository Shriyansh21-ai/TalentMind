"""Module 11 — Background Services.

A framework for recurring maintenance: scheduled tasks, cache/telemetry cleanup,
archive/retention and health polling, driven by the injected clock via
:class:`BackgroundServiceManager`, with a :class:`CronProvider` seam for a future
cron backend.
"""

from __future__ import annotations

from src.platform.runtime.services.background import (
    BackgroundServiceManager,
    BackgroundTask,
    CronProvider,
    ScheduledTask,
    cache_cleanup_task,
    health_polling_task,
    retention_task,
    telemetry_cleanup_task,
)

__all__ = [
    "ScheduledTask",
    "BackgroundTask",
    "CronProvider",
    "BackgroundServiceManager",
    "cache_cleanup_task",
    "telemetry_cleanup_task",
    "retention_task",
    "health_polling_task",
]
