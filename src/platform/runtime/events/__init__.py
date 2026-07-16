"""Module 12 — Runtime Events.

A typed façade over the Milestone 2 enterprise event bus for runtime lifecycle
events (job/worker/queue/cache/health/performance/failure/recovery/metrics),
published onto ``runtime.*`` topics. Reuses the existing bus — no second event
system.
"""

from __future__ import annotations

from src.platform.runtime.events.events import (
    RuntimeEventPublisher,
    RuntimeEventType,
)

__all__ = ["RuntimeEventType", "RuntimeEventPublisher"]
