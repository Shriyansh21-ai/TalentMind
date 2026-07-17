"""Production validation (Module 8).

A :class:`ProductionValidator` that runs a battery of checks across
configuration, platform, runtime, security, AI platform, integrations,
dependencies, environment and deployment readiness, and produces a
:class:`ProductionReadinessReport`. Checks are deterministic and offline:
module presence is probed with :func:`importlib.util.find_spec` (no heavy import
executed), and config/deployment checks use the deployment platform's own
services. A live platform facade may be passed for deeper wiring checks.
"""

from __future__ import annotations

import importlib.util

from pydantic import Field

from src.platform.common.models import PlatformModel
from src.platform.deployment.common.models import CheckSeverity, Environment
from src.platform.deployment.configuration import ConfigurationPlatform
from src.platform.deployment.environment import EnvironmentDetector
from src.platform.deployment.manager import DeploymentManager


class CheckResult(PlatformModel):
    """The outcome of one production-readiness check."""

    category: str
    name: str
    passed: bool
    severity: CheckSeverity = CheckSeverity.INFO
    message: str = ""


class ProductionReadinessReport(PlatformModel):
    """The aggregated production-readiness report."""

    environment: str = ""
    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def critical_failures(self) -> list[CheckResult]:
        """Return failed checks with CRITICAL severity."""
        return [c for c in self.checks if not c.passed and c.severity == CheckSeverity.CRITICAL]

    @property
    def score(self) -> float:
        """Return the fraction of checks that passed (0..1)."""
        return self.passed / self.total if self.total else 0.0

    @property
    def ready(self) -> bool:
        """Return whether the platform is production-ready (no critical failures)."""
        return not self.critical_failures


def _module_present(dotted: str) -> bool:
    """Return whether a module can be located without importing it."""
    try:
        return importlib.util.find_spec(dotted) is not None
    except (ImportError, ValueError):
        return False


class ProductionValidator:
    """Runs production-readiness checks and builds a report."""

    def __init__(
        self,
        *,
        environment: Environment | None = None,
        env_detector: EnvironmentDetector | None = None,
        config_platform: ConfigurationPlatform | None = None,
        deployment_manager: DeploymentManager | None = None,
    ) -> None:
        self._detector = env_detector or EnvironmentDetector()
        self._environment = environment or self._detector.detect()
        self._config = config_platform or ConfigurationPlatform()
        self._deployment = deployment_manager or DeploymentManager()

    def validate(self, *, platform: object | None = None) -> ProductionReadinessReport:
        """Run every check and return the readiness report."""
        checks: list[CheckResult] = []
        checks.extend(self._check_configuration())
        checks.extend(self._check_environment())
        checks.extend(self._check_dependencies())
        checks.extend(self._check_modules())
        checks.extend(self._check_platform(platform))
        checks.extend(self._check_deployment_readiness())
        return ProductionReadinessReport(environment=self._environment.value, checks=checks)

    # -- checks -------------------------------------------------------------

    def _check_configuration(self) -> list[CheckResult]:
        result = self._config.validate(self._config.load("production"))
        return [
            CheckResult(
                category="Configuration",
                name="production_profile_valid",
                passed=result.ok,
                severity=CheckSeverity.CRITICAL,
                message="production configuration valid" if result.ok else "; ".join(result.issues),
            )
        ]

    def _check_environment(self) -> list[CheckResult]:
        env = self._environment
        return [
            CheckResult(
                category="Environment",
                name="environment_detected",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"environment '{env.value}' (offline={env.is_offline})",
            )
        ]

    def _check_dependencies(self) -> list[CheckResult]:
        results: list[CheckResult] = []
        for dep in ["pydantic", "streamlit"]:
            present = _module_present(dep)
            results.append(
                CheckResult(
                    category="Dependencies",
                    name=f"dep:{dep}",
                    passed=present,
                    severity=CheckSeverity.CRITICAL,
                    message=f"{dep} {'available' if present else 'MISSING'}",
                )
            )
        return results

    def _check_modules(self) -> list[CheckResult]:
        # Map readiness categories to the platform packages that back them.
        module_map = {
            "Platform": "src.platform",
            "Runtime": "src.platform.runtime",
            "Security": "src.platform.security",
            "Integrations": "src.platform.integrations",
            "AI Platform": "src.ai",
        }
        results: list[CheckResult] = []
        for category, module in module_map.items():
            present = _module_present(module)
            results.append(
                CheckResult(
                    category=category,
                    name=f"module:{module}",
                    passed=present,
                    severity=CheckSeverity.CRITICAL
                    if category != "AI Platform"
                    else CheckSeverity.WARNING,
                    message=f"{module} {'present' if present else 'MISSING'}",
                )
            )
        return results

    def _check_platform(self, platform: object | None) -> list[CheckResult]:
        if platform is None:
            return [
                CheckResult(
                    category="Platform",
                    name="live_facade",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message="no live platform provided — static checks only",
                )
            ]
        results: list[CheckResult] = []
        for attr in ["organizations", "runtime", "security", "integrations"]:
            ok = hasattr(platform, attr)
            results.append(
                CheckResult(
                    category="Platform",
                    name=f"facade:{attr}",
                    passed=ok,
                    severity=CheckSeverity.CRITICAL,
                    message=f"platform.{attr} {'wired' if ok else 'MISSING'}",
                )
            )
        return results

    def _check_deployment_readiness(self) -> list[CheckResult]:
        profile = self._deployment.get_profile("production")
        validation = self._deployment.validate(profile)
        return [
            CheckResult(
                category="Deployment Readiness",
                name="production_profile_deployable",
                passed=validation.ok,
                severity=CheckSeverity.CRITICAL,
                message="production profile deployable"
                if validation.ok
                else "; ".join(i.message for i in validation.issues),
            )
        ]
