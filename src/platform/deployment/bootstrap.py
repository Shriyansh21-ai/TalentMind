"""Deployment platform composition root (Module 15).

Wires the Enterprise Deployment Platform into one lazily-constructed
:class:`DeploymentPlatform` facade using the shared
:class:`~src.platform.container.Container`. Services share a single injected
:class:`Clock` and are lazy singletons built at most once.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.common.clock import Clock, SystemClock
from src.platform.container import Container
from src.platform.deployment.backup import BackupManager
from src.platform.deployment.benchmark import BenchmarkRunner
from src.platform.deployment.configuration import ConfigurationPlatform
from src.platform.deployment.environment import EnvironmentDetector
from src.platform.deployment.manager import DeploymentManager
from src.platform.deployment.release import ReleaseManager
from src.platform.deployment.validation import ProductionValidator


@dataclass
class DeploymentPlatform:
    """A fully-wired deployment platform exposing every module's service."""

    container: Container
    clock: Clock

    @property
    def environment(self) -> EnvironmentDetector:
        return self.container.resolve("dep.environment")  # type: ignore[return-value]

    @property
    def deployments(self) -> DeploymentManager:
        return self.container.resolve("dep.manager")  # type: ignore[return-value]

    @property
    def configuration(self) -> ConfigurationPlatform:
        return self.container.resolve("dep.configuration")  # type: ignore[return-value]

    @property
    def backups(self) -> BackupManager:
        return self.container.resolve("dep.backup")  # type: ignore[return-value]

    @property
    def releases(self) -> ReleaseManager:
        return self.container.resolve("dep.release")  # type: ignore[return-value]

    @property
    def validator(self) -> ProductionValidator:
        return self.container.resolve("dep.validator")  # type: ignore[return-value]

    @property
    def benchmarks(self) -> BenchmarkRunner:
        return self.container.resolve("dep.benchmark")  # type: ignore[return-value]


def build_deployment_platform(*, clock: Clock | None = None) -> DeploymentPlatform:
    """Compose and return a fully-wired :class:`DeploymentPlatform`."""
    the_clock = clock or SystemClock()
    container = Container()

    container.register("dep.environment", lambda _c: EnvironmentDetector())
    container.register("dep.manager", lambda _c: DeploymentManager(clock=the_clock))
    container.register("dep.configuration", lambda _c: ConfigurationPlatform())
    container.register("dep.backup", lambda _c: BackupManager(clock=the_clock))
    container.register("dep.release", lambda _c: ReleaseManager(clock=the_clock))
    container.register("dep.benchmark", lambda _c: BenchmarkRunner())
    container.register(
        "dep.validator",
        lambda c: ProductionValidator(
            env_detector=c.resolve("dep.environment"),  # type: ignore[arg-type]
            config_platform=c.resolve("dep.configuration"),  # type: ignore[arg-type]
            deployment_manager=c.resolve("dep.manager"),  # type: ignore[arg-type]
        ),
    )

    return DeploymentPlatform(container=container, clock=the_clock)
