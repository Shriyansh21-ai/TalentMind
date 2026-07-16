"""Module 7 — Load Management.

Concurrency manager, bulkhead isolation, rate control, backpressure, adaptive
throttling, resource limits and the shared circuit breaker — composed into a
:class:`LoadManager`. Includes future-autoscaling hooks (recommended limits).
"""

from __future__ import annotations

from src.platform.runtime.load.manager import (
    AdaptiveThrottle,
    BackpressureController,
    Bulkhead,
    ConcurrencyManager,
    LoadManager,
    RateControl,
)
from src.platform.runtime.load.models import BackpressureSignal, ResourceLimits
from src.platform.runtime.resilience.policies import CircuitBreaker, CircuitState

__all__ = [
    "ConcurrencyManager",
    "Bulkhead",
    "RateControl",
    "BackpressureController",
    "BackpressureSignal",
    "AdaptiveThrottle",
    "ResourceLimits",
    "LoadManager",
    "CircuitBreaker",
    "CircuitState",
]
