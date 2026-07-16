"""Deployment-platform exception hierarchy (Phase 6 / Milestone 5).

Extends the platform-wide :class:`~src.platform.common.errors.PlatformError`
hierarchy with errors specific to production deployment, configuration, backup,
release and validation concerns. No business logic lives here.
"""

from __future__ import annotations

from src.platform.common.errors import PlatformError


class DeploymentError(PlatformError):
    """Base class for every deployment-platform error."""

    code = "deployment_error"


class DeploymentValidationError(DeploymentError):
    """Raised when a deployment profile or plan fails validation."""

    code = "deployment_validation_error"


class RollbackError(DeploymentError):
    """Raised when a rollback cannot be planned or applied."""

    code = "rollback_error"


class ConfigurationPlatformError(DeploymentError):
    """Raised on an invalid configuration profile / load / export."""

    code = "configuration_platform_error"


class BackupError(DeploymentError):
    """Raised on an invalid backup or restore operation."""

    code = "backup_error"


class ReleaseError(DeploymentError):
    """Raised on an invalid release / version operation."""

    code = "release_error"


class BenchmarkError(DeploymentError):
    """Raised on an invalid benchmark operation."""

    code = "benchmark_error"
