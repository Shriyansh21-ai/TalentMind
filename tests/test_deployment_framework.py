"""Modules 1, 5, 6, 7 tests — deployment manager, configuration, backup, release.

Environment detection, profile validation + planning + deploy/rollback lifecycle,
configuration profiles/loader/validation/export, backup/restore/recovery, and
release engineering (semver, notes, compatibility, migrations, deprecations).
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.deployment.backup import BackupManager, BackupType
from src.platform.deployment.common.errors import (
    BackupError,
    DeploymentValidationError,
    ReleaseError,
)
from src.platform.deployment.common.models import DeploymentStatus, Environment
from src.platform.deployment.configuration import ConfigurationPlatform
from src.platform.deployment.environment import EnvironmentDetector
from src.platform.deployment.manager import DeploymentManager
from src.platform.deployment.models import DeploymentProfile, DeploymentTarget
from src.platform.deployment.common.models import DeploymentTargetType
from src.platform.deployment.release import (
    ChangeEntry,
    ChangeType,
    ReleaseManager,
    SemanticVersion,
)


# -- environment detection --------------------------------------------------


def test_environment_defaults_to_development():
    assert EnvironmentDetector({}).detect() == Environment.DEVELOPMENT


def test_environment_aliases_and_direct():
    assert EnvironmentDetector({"TALENTMIND_ENV": "prod"}).detect() == Environment.PRODUCTION
    assert EnvironmentDetector({"TALENTMIND_ENV": "offline"}).detect() == Environment.OFFLINE_ENTERPRISE
    assert EnvironmentDetector({"TALENTMIND_ENV": "staging"}).detect() == Environment.STAGING
    assert EnvironmentDetector({"TALENTMIND_ENV": "bogus"}).detect() == Environment.DEVELOPMENT


def test_environment_offline_and_production_flags():
    assert EnvironmentDetector({"TALENTMIND_ENV": "air_gapped"}).is_offline()
    assert EnvironmentDetector({"TALENTMIND_ENV": "production"}).is_production()


# -- deployment manager -----------------------------------------------------


def test_builtin_profiles_cover_all_environments():
    mgr = DeploymentManager(clock=FrozenClock())
    envs = {p.environment for p in mgr.list_profiles()}
    assert envs == set(Environment)


def test_validate_flags_offline_with_region():
    mgr = DeploymentManager(clock=FrozenClock())
    bad = DeploymentProfile(
        name="bad-offline", environment=Environment.OFFLINE_ENTERPRISE,
        target=DeploymentTarget(target_type=DeploymentTargetType.KUBERNETES, region="us-east-1"),
        offline=True,
    )
    result = mgr.validate(bad)
    assert not result.ok and result.has_critical


def test_deploy_and_rollback_lifecycle():
    mgr = DeploymentManager(clock=FrozenClock())
    profile = mgr.get_profile("production")
    deployment = mgr.deploy(profile, previous_version="0.9.0")
    assert deployment.status == DeploymentStatus.DEPLOYED
    assert deployment.plan is not None and deployment.plan.step_count > 0
    assert deployment.rollback_plan is not None
    assert deployment.health.is_healthy
    rolled = mgr.rollback(deployment.id)
    assert rolled.status == DeploymentStatus.ROLLED_BACK


def test_deploy_rejects_invalid_profile():
    mgr = DeploymentManager(clock=FrozenClock())
    invalid = DeploymentProfile(name="invalid", replicas=0, config_profile="")
    with pytest.raises(DeploymentValidationError):
        mgr.deploy(invalid)


def test_kubernetes_plan_includes_manifests_and_hpa():
    mgr = DeploymentManager(clock=FrozenClock())
    plan = mgr.create_plan(mgr.get_profile("production"))
    actions = {s.action for s in plan.steps}
    assert "kubectl_apply" in actions
    assert "configure_hpa" in actions


# -- configuration platform -------------------------------------------------


def test_config_load_merges_over_base():
    cfg = ConfigurationPlatform()
    production = cfg.load("production")
    assert production["workers"] == 4
    assert production["app_name"] == "talentmind"  # inherited from base


def test_config_validation_catches_bad_values():
    cfg = ConfigurationPlatform()
    result = cfg.validate({"app_name": "x", "log_level": "NOPE", "workers": 0,
                           "cache_ttl_seconds": 1, "telemetry_enabled": True, "offline": False})
    assert not result.ok
    assert any("log_level" in i for i in result.issues)
    assert any("workers" in i for i in result.issues)


def test_config_export_formats():
    cfg = ConfigurationPlatform()
    assert cfg.export("offline", fmt="env").startswith("TALENTMIND_")
    assert '"workers"' in cfg.export("offline", fmt="json")
    assert "offline: true" in cfg.export("offline", fmt="yaml")


def test_offline_profile_sets_offline_true():
    cfg = ConfigurationPlatform()
    assert cfg.load("offline")["offline"] is True


# -- backup & recovery ------------------------------------------------------


def test_backup_and_restore_roundtrip():
    mgr = BackupManager(clock=FrozenClock())
    manifest = mgr.backup(BackupType.CONFIGURATION, {"a": 1, "b": [1, 2, 3]})
    assert mgr.validate_restore(manifest.id).valid
    assert mgr.restore(manifest.id) == {"a": 1, "b": [1, 2, 3]}


def test_restore_detects_corruption():
    mgr = BackupManager(clock=FrozenClock())
    manifest = mgr.backup(BackupType.AUDIT, {"x": 1})
    mgr.provider.put(manifest.location, b"tampered")  # corrupt the stored bytes
    validation = mgr.validate_restore(manifest.id)
    assert not validation.valid
    with pytest.raises(BackupError):
        mgr.restore(manifest.id)


def test_recovery_plan_and_report():
    mgr = BackupManager(clock=FrozenClock())
    mgr.backup(BackupType.CONFIGURATION, {"a": 1})
    mgr.backup(BackupType.METADATA, {"m": 2})
    plan = mgr.recovery_plan()
    assert plan.rto_minutes > 0 and len(plan.steps) > 0
    report = mgr.recovery_report()
    assert report.all_valid
    assert "configuration" in report.restored_types


# -- release engineering ----------------------------------------------------


def test_semver_parse_and_compare():
    assert str(SemanticVersion.parse("1.2.3")) == "1.2.3"
    assert SemanticVersion.parse("2.0.0").is_newer_than(SemanticVersion.parse("1.9.9"))
    assert SemanticVersion.parse("1.0.0").is_newer_than(SemanticVersion.parse("1.0.0-rc1"))
    with pytest.raises(ReleaseError):
        SemanticVersion.parse("not.a.version")


def test_release_notes_grouped_by_type():
    mgr = ReleaseManager(clock=FrozenClock())
    manifest = mgr.register_release("1.0.0", changes=[
        ChangeEntry(change_type=ChangeType.FEATURE, summary="Deployment platform"),
        ChangeEntry(change_type=ChangeType.FIX, summary="Fixed a bug"),
    ])
    assert "✨ Features" in manifest.notes
    assert "🐛 Fixes" in manifest.notes
    assert mgr.latest() == "1.0.0"


def test_suggest_bump_rules():
    mgr = ReleaseManager(clock=FrozenClock())
    assert mgr.suggest_bump("1.2.3", [ChangeEntry(change_type=ChangeType.BREAKING, summary="x")]) == "2.0.0"
    assert mgr.suggest_bump("1.2.3", [ChangeEntry(change_type=ChangeType.FEATURE, summary="x")]) == "1.3.0"
    assert mgr.suggest_bump("1.2.3", [ChangeEntry(change_type=ChangeType.FIX, summary="x")]) == "1.2.4"


def test_compatibility_migrations_deprecations():
    mgr = ReleaseManager(clock=FrozenClock())
    mgr.set_compatibility("1.0.0", "1.0.0")
    assert mgr.is_compatible("1.0.0", "1.2.0")
    assert not mgr.is_compatible("1.0.0", "0.9.0")
    mgr.track_migration("m1", "0.9.0", "1.0.0")
    assert len(mgr.pending_migrations()) == 1
    mgr.apply_migration("m1")
    assert mgr.pending_migrations() == []
    mgr.deprecate("old_api", "1.0.0", remove_in_version="2.0.0")
    assert len(mgr.deprecations()) == 1
