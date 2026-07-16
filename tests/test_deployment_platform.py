"""Modules 8, 9, 13, 16 + composition/architecture tests for the deployment platform.

Production validator, benchmark framework, packaging, repository health check,
composition root wiring, the additive-architecture rule, reachability from the
main platform facade, and an end-to-end production-readiness flow.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.platform.bootstrap import build_platform
from src.platform.common.clock import FrozenClock
from src.platform.deployment import (
    build_deployment_platform,
    package_info,
    verify_installation,
)
from src.platform.deployment.benchmark import BenchmarkCategory, BenchmarkRunner
from src.platform.deployment.health_check import RepositoryHealthCheck
from src.platform.deployment.validation import ProductionValidator

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_DIR = ROOT / "src" / "platform" / "deployment"

_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from|import)\s+src\."
    r"(scoring|semantic|intelligence|hiring|recruiter|pipeline|reasoning|"
    r"ingestion|insights|comparison|talent_pool|interview|filtering|dashboard|"
    r"llm|ai|models)\b",
    re.MULTILINE,
)


# -- architecture -----------------------------------------------------------


def test_deployment_never_imports_business_logic():
    offenders: list[str] = []
    for path in DEPLOYMENT_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"deployment imported business logic: {offenders}"


def test_every_deployment_subpackage_imports():
    import importlib

    for name in [
        "common", "manager", "environment", "configuration", "backup",
        "release", "validation", "benchmark", "packaging", "health_check",
        "bootstrap",
    ]:
        importlib.import_module(f"src.platform.deployment.{name}")


def test_infra_artifacts_present():
    for artifact in [
        "Dockerfile", "docker-compose.yml", "docker-compose.dev.yml",
        "docker-compose.prod.yml", ".dockerignore", "pyproject.toml",
        "k8s/05-deployment.yaml", "k8s/08-hpa.yaml",
        ".github/workflows/ci.yml", ".github/workflows/release.yml",
        "docs/DEVELOPER_GUIDE.md", "docs/ARCHITECTURE.md",
        "docs/DISASTER_RECOVERY.md", "docs/INSTALL.md",
    ]:
        assert (ROOT / artifact).exists(), f"missing infra artifact: {artifact}"


# -- production validation --------------------------------------------------


def test_production_validator_is_ready():
    report = ProductionValidator().validate()
    assert report.ready
    assert report.critical_failures == []
    assert report.score == 1.0


def test_production_validator_deep_check_with_platform():
    platform = build_platform(clock=FrozenClock())
    report = build_deployment_platform().validator.validate(platform=platform)
    facade_checks = [c for c in report.checks if c.name.startswith("facade:")]
    assert facade_checks and all(c.passed for c in facade_checks)


# -- benchmark --------------------------------------------------------------


def test_benchmark_records_real_statistics():
    runner = BenchmarkRunner()
    result = runner.run("sum", BenchmarkCategory.THROUGHPUT, lambda: sum(range(50)), iterations=25)
    assert result.iterations == 25
    assert result.min_ms >= 0 and result.max_ms >= result.min_ms
    assert result.avg_ms >= 0 and result.ops_per_second >= 0
    report = runner.report()
    assert len(report.results) == 1
    assert report.by_category(BenchmarkCategory.THROUGHPUT)


# -- packaging --------------------------------------------------------------


def test_package_info_and_installation():
    info = package_info()
    assert info.name == "talentmind" and info.version == "1.0.0"
    report = verify_installation()
    assert report.valid  # required deps present in the test environment
    assert report.offline_capable


# -- repository health ------------------------------------------------------


def test_repository_health_is_clean():
    summary = RepositoryHealthCheck().run()
    assert summary.modules_scanned > 100
    assert summary.import_errors == []
    assert summary.additive_violations == []
    assert summary.naming_issues == []
    assert summary.healthy


# -- composition & reachability --------------------------------------------


def test_build_deployment_platform_wires_all_services():
    dp = build_deployment_platform(clock=FrozenClock())
    for key in [
        "dep.environment", "dep.manager", "dep.configuration", "dep.backup",
        "dep.release", "dep.benchmark", "dep.validator",
    ]:
        assert dp.container.has(key)
    assert dp.deployments is dp.deployments  # lazy singleton


def test_deployment_reachable_from_main_platform():
    main = build_platform(clock=FrozenClock())
    assert main.deployment is main.deployment
    assert main.deployment.validator.validate().ready


def test_all_phase6_platforms_coexist():
    main = build_platform(clock=FrozenClock())
    # Every Phase 6 sub-platform is reachable from the one facade.
    assert main.integrations is not None
    assert main.runtime is not None
    assert main.security is not None
    assert main.deployment is not None
