"""Shared foundation for the Enterprise Runtime Platform.

The runtime error hierarchy and shared value types (health states, severities)
reused across the jobs, workers, execution, cache, health, load and resilience
modules.
"""

from __future__ import annotations

from src.platform.runtime.common.errors import (
    CircuitOpenError,
    ConcurrencyLimitError,
    JobCancelledError,
    JobError,
    JobNotFoundError,
    QueueOverflowError,
    ResourceLimitError,
    RuntimePlatformError,
    RuntimeValidationError,
    TaskTimeoutError,
    WorkerError,
)
from src.platform.runtime.common.models import HealthState, Severity

__all__ = [
    "RuntimePlatformError",
    "JobError",
    "JobNotFoundError",
    "JobCancelledError",
    "QueueOverflowError",
    "WorkerError",
    "TaskTimeoutError",
    "CircuitOpenError",
    "ConcurrencyLimitError",
    "ResourceLimitError",
    "RuntimeValidationError",
    "HealthState",
    "Severity",
]
