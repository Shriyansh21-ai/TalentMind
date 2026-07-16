"""Shared deployment value types (Module 15 · Module 1)."""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """A deployment environment / topology."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    AIR_GAPPED = "air_gapped"
    OFFLINE_ENTERPRISE = "offline_enterprise"
    CLOUD = "cloud"
    HYBRID = "hybrid"

    @property
    def is_production_like(self) -> bool:
        """Return whether this environment demands production-grade rigor."""
        return self in (
            Environment.STAGING,
            Environment.PRODUCTION,
            Environment.AIR_GAPPED,
            Environment.OFFLINE_ENTERPRISE,
            Environment.CLOUD,
            Environment.HYBRID,
        )

    @property
    def is_offline(self) -> bool:
        """Return whether this environment is offline by design."""
        return self in (Environment.AIR_GAPPED, Environment.OFFLINE_ENTERPRISE)


class DeploymentTargetType(str, Enum):
    """Where a deployment runs."""

    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    VIRTUAL_MACHINE = "vm"
    SERVERLESS = "serverless"


class DeploymentStatus(str, Enum):
    """The lifecycle state of a deployment."""

    PENDING = "pending"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

    @property
    def is_terminal(self) -> bool:
        """Return whether no further transition is expected."""
        return self in (
            DeploymentStatus.DEPLOYED,
            DeploymentStatus.FAILED,
            DeploymentStatus.ROLLED_BACK,
        )


class HealthState(str, Enum):
    """A coarse health signal for a deployment."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckSeverity(str, Enum):
    """Severity of a validation / readiness check."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
