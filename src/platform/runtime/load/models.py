"""Load-management value objects (Module 7)."""

from __future__ import annotations

from enum import Enum

from src.platform.common.models import PlatformModel


class BackpressureSignal(str, Enum):
    """The decision a backpressure controller returns for new work."""

    ACCEPT = "accept"
    THROTTLE = "throttle"
    REJECT = "reject"


class ResourceLimits(PlatformModel):
    """Configured upper bounds the runtime enforces (Module 15)."""

    max_concurrent_jobs: int = 100
    max_queue_depth: int = 10_000
    max_workers: int = 50
    max_payload_bytes: int = 5_000_000
