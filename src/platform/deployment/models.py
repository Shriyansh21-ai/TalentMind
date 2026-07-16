"""Deployment models (Module 1).

The vocabulary of the deployment platform: profiles (how to deploy into an
environment), targets (where), metadata (which build), plans + rollback plans
(the ordered steps), and the deployment record itself with its status and
health. Platform-level (not tenant-scoped) — deployments describe the running
platform, not customer data.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from src.platform.common.models import Entity, PlatformModel
from src.platform.deployment.common.models import (
    DeploymentStatus,
    DeploymentTargetType,
    Environment,
    HealthState,
)


class ResourceLimits(PlatformModel):
    """Container/pod resource requests and limits."""

    cpu_request: str = "250m"
    cpu_limit: str = "1000m"
    memory_request: str = "512Mi"
    memory_limit: str = "2Gi"


class DeploymentTarget(PlatformModel):
    """Where a deployment runs."""

    target_type: DeploymentTargetType = DeploymentTargetType.DOCKER
    endpoint: str = ""
    region: str = ""
    namespace: str = "talentmind"


class DeploymentProfile(PlatformModel):
    """A named recipe for deploying into a particular environment."""

    name: str
    environment: Environment = Environment.DEVELOPMENT
    target: DeploymentTarget = Field(default_factory=DeploymentTarget)
    replicas: int = 1
    resources: ResourceLimits = Field(default_factory=ResourceLimits)
    offline: bool = False
    autoscale: bool = False
    min_replicas: int = 1
    max_replicas: int = 1
    config_profile: str = "development"
    features: dict[str, bool] = Field(default_factory=dict)


class DeploymentMetadata(PlatformModel):
    """Which build a deployment corresponds to."""

    version: str = "1.0.0"
    build_id: str = ""
    git_sha: str = ""
    deployer: str = "system"
    channel: str = "stable"


class DeploymentStep(PlatformModel):
    """One ordered step in a deployment or rollback plan."""

    order: int
    name: str
    action: str
    description: str = ""


class DeploymentPlan(Entity):
    """An ordered set of steps to realise a deployment profile."""

    profile_name: str
    environment: Environment = Environment.DEVELOPMENT
    steps: list[DeploymentStep] = Field(default_factory=list)

    @property
    def step_count(self) -> int:
        """Return the number of steps in the plan."""
        return len(self.steps)


class RollbackPlan(Entity):
    """An ordered set of steps to revert to a previous version."""

    from_version: str = ""
    to_version: str = ""
    steps: list[DeploymentStep] = Field(default_factory=list)


class DeploymentHealth(PlatformModel):
    """A point-in-time health snapshot for a deployment."""

    state: HealthState = HealthState.UNKNOWN
    message: str = ""
    ready_replicas: int = 0
    desired_replicas: int = 0

    @property
    def is_healthy(self) -> bool:
        """Return whether the deployment is healthy."""
        return self.state == HealthState.HEALTHY


class Deployment(Entity):
    """A deployment record: profile + target + metadata + status + plans."""

    profile: DeploymentProfile
    metadata: DeploymentMetadata = Field(default_factory=DeploymentMetadata)
    status: DeploymentStatus = DeploymentStatus.PENDING
    plan: DeploymentPlan | None = None
    rollback_plan: RollbackPlan | None = None
    health: DeploymentHealth = Field(default_factory=DeploymentHealth)
    history: list[str] = Field(default_factory=list)
    deployed_at: datetime | None = None
