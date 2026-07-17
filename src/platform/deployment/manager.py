"""Deployment manager (Module 1 — the deployment control plane).

Registers deployment profiles (with built-in profiles for every supported
environment), validates them, builds deterministic deployment + rollback plans,
drives a deployment through its status lifecycle, and reports health. Everything
is deterministic and offline — it *plans and records* deployments; it does not
shell out to Docker/Kubernetes (a future executor binds behind the same plan).
"""

from __future__ import annotations

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import PlatformModel
from src.platform.common.repository import InMemoryRepository
from src.platform.deployment.common.errors import (
    DeploymentValidationError,
    RollbackError,
)
from src.platform.deployment.common.models import (
    CheckSeverity,
    DeploymentStatus,
    DeploymentTargetType,
    Environment,
    HealthState,
)
from src.platform.deployment.models import (
    Deployment,
    DeploymentHealth,
    DeploymentMetadata,
    DeploymentPlan,
    DeploymentProfile,
    DeploymentStep,
    DeploymentTarget,
    ResourceLimits,
    RollbackPlan,
)


class ValidationIssue(PlatformModel):
    """A single deployment-validation finding."""

    check: str
    severity: CheckSeverity = CheckSeverity.WARNING
    message: str = ""


class DeploymentValidation(PlatformModel):
    """The result of validating a deployment profile."""

    profile_name: str
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        """Return whether any critical issue was found."""
        return any(i.severity == CheckSeverity.CRITICAL for i in self.issues)

    @property
    def ok(self) -> bool:
        """Return whether the profile is deployable (no critical issues)."""
        return not self.has_critical


def _default_profiles() -> dict[str, DeploymentProfile]:
    """Return built-in profiles for every supported environment."""
    k8s = DeploymentTargetType.KUBERNETES
    docker = DeploymentTargetType.DOCKER
    local = DeploymentTargetType.LOCAL
    profiles = [
        DeploymentProfile(
            name="development",
            environment=Environment.DEVELOPMENT,
            target=DeploymentTarget(target_type=local),
            config_profile="development",
        ),
        DeploymentProfile(
            name="testing",
            environment=Environment.TESTING,
            target=DeploymentTarget(target_type=docker),
            config_profile="testing",
        ),
        DeploymentProfile(
            name="staging",
            environment=Environment.STAGING,
            target=DeploymentTarget(target_type=k8s),
            replicas=2,
            autoscale=True,
            min_replicas=2,
            max_replicas=4,
            config_profile="production",
        ),
        DeploymentProfile(
            name="production",
            environment=Environment.PRODUCTION,
            target=DeploymentTarget(target_type=k8s),
            replicas=3,
            autoscale=True,
            min_replicas=3,
            max_replicas=10,
            resources=ResourceLimits(cpu_limit="2000m", memory_limit="4Gi"),
            config_profile="production",
        ),
        DeploymentProfile(
            name="air_gapped",
            environment=Environment.AIR_GAPPED,
            target=DeploymentTarget(target_type=k8s),
            replicas=2,
            offline=True,
            config_profile="offline",
        ),
        DeploymentProfile(
            name="offline_enterprise",
            environment=Environment.OFFLINE_ENTERPRISE,
            target=DeploymentTarget(target_type=docker),
            replicas=1,
            offline=True,
            config_profile="offline",
        ),
        DeploymentProfile(
            name="cloud",
            environment=Environment.CLOUD,
            target=DeploymentTarget(target_type=k8s, region="us-east-1"),
            replicas=3,
            autoscale=True,
            min_replicas=3,
            max_replicas=20,
            config_profile="cloud",
        ),
        DeploymentProfile(
            name="hybrid",
            environment=Environment.HYBRID,
            target=DeploymentTarget(target_type=k8s),
            replicas=2,
            autoscale=True,
            min_replicas=2,
            max_replicas=8,
            config_profile="enterprise",
        ),
    ]
    return {p.name: p for p in profiles}


class DeploymentManager:
    """Register, validate, plan, deploy and roll back deployment profiles."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._profiles: dict[str, DeploymentProfile] = _default_profiles()
        self.repo: InMemoryRepository[Deployment] = InMemoryRepository("deployment")

    # -- profiles -----------------------------------------------------------

    def register_profile(self, profile: DeploymentProfile) -> DeploymentProfile:
        """Register (or replace) a deployment profile."""
        self._profiles[profile.name] = profile
        return profile

    def get_profile(self, name: str) -> DeploymentProfile:
        """Return a profile by name or raise."""
        profile = self._profiles.get(name)
        if profile is None:
            raise DeploymentValidationError(f"unknown deployment profile '{name}'")
        return profile

    def list_profiles(self) -> list[DeploymentProfile]:
        """Return every registered profile."""
        return list(self._profiles.values())

    # -- validation ---------------------------------------------------------

    def validate(self, profile: DeploymentProfile) -> DeploymentValidation:
        """Validate a profile and return the (non-raising) result."""
        issues: list[ValidationIssue] = []
        if profile.replicas < 1:
            issues.append(
                ValidationIssue(
                    check="replicas",
                    severity=CheckSeverity.CRITICAL,
                    message="replicas must be >= 1",
                )
            )
        if profile.autoscale:
            if profile.min_replicas > profile.max_replicas:
                issues.append(
                    ValidationIssue(
                        check="autoscale",
                        severity=CheckSeverity.CRITICAL,
                        message="min_replicas exceeds max_replicas",
                    )
                )
            if profile.max_replicas < profile.replicas:
                issues.append(
                    ValidationIssue(
                        check="autoscale",
                        severity=CheckSeverity.WARNING,
                        message="max_replicas below desired replicas",
                    )
                )
        if profile.environment.is_production_like and profile.replicas < 2 and not profile.offline:
            issues.append(
                ValidationIssue(
                    check="ha",
                    severity=CheckSeverity.WARNING,
                    message="production-like env should run >= 2 replicas",
                )
            )
        if profile.offline and profile.target.region:
            issues.append(
                ValidationIssue(
                    check="offline",
                    severity=CheckSeverity.CRITICAL,
                    message="offline profile must not target a cloud region",
                )
            )
        if not profile.config_profile:
            issues.append(
                ValidationIssue(
                    check="config",
                    severity=CheckSeverity.CRITICAL,
                    message="config_profile is required",
                )
            )
        return DeploymentValidation(profile_name=profile.name, issues=issues)

    # -- planning -----------------------------------------------------------

    def create_plan(self, profile: DeploymentProfile) -> DeploymentPlan:
        """Build a deterministic, ordered deployment plan for a profile."""
        steps = [
            DeploymentStep(
                order=1,
                name="validate",
                action="validate_profile",
                description="Validate profile and environment",
            ),
            DeploymentStep(
                order=2,
                name="load_config",
                action="load_configuration",
                description=f"Load '{profile.config_profile}' configuration profile",
            ),
            DeploymentStep(
                order=3,
                name="provision",
                action="provision_target",
                description=f"Provision {profile.target.target_type.value} target",
            ),
        ]
        if profile.target.target_type == DeploymentTargetType.KUBERNETES:
            steps.append(
                DeploymentStep(
                    order=len(steps) + 1,
                    name="apply_manifests",
                    action="kubectl_apply",
                    description="Apply k8s manifests",
                )
            )
            if profile.autoscale:
                steps.append(
                    DeploymentStep(
                        order=len(steps) + 1,
                        name="hpa",
                        action="configure_hpa",
                        description="Configure autoscaling",
                    )
                )
        elif profile.target.target_type == DeploymentTargetType.DOCKER:
            steps.append(
                DeploymentStep(
                    order=len(steps) + 1,
                    name="compose_up",
                    action="docker_compose_up",
                    description="Start containers",
                )
            )
        steps.append(
            DeploymentStep(
                order=len(steps) + 1,
                name="healthcheck",
                action="verify_health",
                description="Verify deployment health",
            )
        )
        steps.append(
            DeploymentStep(
                order=len(steps) + 1,
                name="smoke_test",
                action="smoke_test",
                description="Run smoke tests",
            )
        )
        now = self._clock.now()
        return DeploymentPlan(
            id=generate_id("plan"),
            profile_name=profile.name,
            environment=profile.environment,
            steps=steps,
            created_at=now,
            updated_at=now,
        )

    def create_rollback_plan(self, from_version: str, to_version: str) -> RollbackPlan:
        """Build a deterministic rollback plan between two versions."""
        if not to_version:
            raise RollbackError("rollback requires a target version")
        now = self._clock.now()
        steps = [
            DeploymentStep(
                order=1, name="halt", action="halt_traffic", description="Stop routing new traffic"
            ),
            DeploymentStep(
                order=2,
                name="restore_version",
                action="deploy_version",
                description=f"Redeploy version {to_version}",
            ),
            DeploymentStep(
                order=3,
                name="restore_config",
                action="restore_configuration",
                description="Restore the previous configuration",
            ),
            DeploymentStep(
                order=4,
                name="verify",
                action="verify_health",
                description="Verify rolled-back deployment health",
            ),
            DeploymentStep(
                order=5,
                name="resume",
                action="resume_traffic",
                description="Resume traffic routing",
            ),
        ]
        return RollbackPlan(
            id=generate_id("rbk"),
            from_version=from_version,
            to_version=to_version,
            steps=steps,
            created_at=now,
            updated_at=now,
        )

    # -- lifecycle ----------------------------------------------------------

    def deploy(
        self,
        profile: DeploymentProfile,
        *,
        metadata: DeploymentMetadata | None = None,
        previous_version: str = "",
    ) -> Deployment:
        """Plan, validate and record a deployment (raises on critical issues)."""
        now = self._clock.now()
        meta = metadata or DeploymentMetadata()
        deployment = Deployment(
            id=generate_id("dep"),
            profile=profile,
            metadata=meta,
            status=DeploymentStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self.repo.add(deployment)

        self._transition(deployment, DeploymentStatus.VALIDATING, "validating profile")
        validation = self.validate(profile)
        if not validation.ok:
            self._transition(deployment, DeploymentStatus.FAILED, "validation failed")
            raise DeploymentValidationError(
                f"profile '{profile.name}' failed validation: "
                + "; ".join(
                    i.message for i in validation.issues if i.severity == CheckSeverity.CRITICAL
                )
            )

        deployment.plan = self.create_plan(profile)
        deployment.rollback_plan = self.create_rollback_plan(
            meta.version, previous_version or meta.version
        )
        self._transition(deployment, DeploymentStatus.DEPLOYING, "executing plan")

        deployment.health = DeploymentHealth(
            state=HealthState.HEALTHY,
            message="deployment healthy",
            ready_replicas=profile.replicas,
            desired_replicas=profile.replicas,
        )
        deployment.deployed_at = self._clock.now()
        self._transition(deployment, DeploymentStatus.DEPLOYED, "deployment complete")
        return deployment

    def rollback(self, deployment_id: str) -> Deployment:
        """Apply a deployment's rollback plan (→ ROLLED_BACK)."""
        deployment = self.repo.require(deployment_id)
        if deployment.rollback_plan is None:
            raise RollbackError(f"deployment '{deployment_id}' has no rollback plan")
        self._transition(
            deployment,
            DeploymentStatus.ROLLED_BACK,
            f"rolled back to {deployment.rollback_plan.to_version}",
        )
        deployment.health = DeploymentHealth(
            state=HealthState.HEALTHY,
            message="rolled back",
            ready_replicas=deployment.profile.replicas,
            desired_replicas=deployment.profile.replicas,
        )
        return self.repo.update(deployment)

    # -- queries ------------------------------------------------------------

    def get(self, deployment_id: str) -> Deployment:
        """Return one deployment record."""
        return self.repo.require(deployment_id)

    def list_deployments(self) -> list[Deployment]:
        """Return every deployment record (newest last, insertion order)."""
        return self.repo.list()

    def health(self, deployment_id: str) -> DeploymentHealth:
        """Return a deployment's current health."""
        return self.repo.require(deployment_id).health

    def _transition(self, deployment: Deployment, status: DeploymentStatus, note: str) -> None:
        deployment.status = status
        deployment.history.append(f"{status.value}: {note}")
        deployment.touch(self._clock.now())
        self.repo.update(deployment)
