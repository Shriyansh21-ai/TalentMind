"""Shared runtime enums and value objects (Module 14 · Module 18).

Small, dependency-light types reused across the runtime modules so there is one
definition of each concept (health states, severities) rather than a copy per
module.
"""

from __future__ import annotations

from enum import Enum


class HealthState(str, Enum):
    """A coarse health signal shared by every runtime component.

    Ordered by severity so aggregation can pick the worst state.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

    @property
    def severity(self) -> int:
        """Return an ordinal where a higher number is worse."""
        return {
            HealthState.HEALTHY: 0,
            HealthState.UNKNOWN: 1,
            HealthState.DEGRADED: 2,
            HealthState.UNHEALTHY: 3,
        }[self]

    @classmethod
    def worst(cls, states: list[HealthState]) -> HealthState:
        """Return the most severe state in ``states`` (HEALTHY if empty)."""
        if not states:
            return cls.HEALTHY
        return max(states, key=lambda s: s.severity)


class Severity(str, Enum):
    """Severity level for runtime events and log lines."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
