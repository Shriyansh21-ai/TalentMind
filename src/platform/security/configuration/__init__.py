"""Module 11 — Configuration Governance.

Versioned, tenant-scoped configuration with validation, an approval workflow,
change tracking, exact rollback and environment profiles via
:class:`ConfigurationGovernanceService`.
"""

from __future__ import annotations

from src.platform.security.configuration.models import (
    ChangeRequest,
    ChangeStatus,
    ConfigEntry,
    ConfigScope,
    ConfigStatus,
    ConfigVersion,
    EnvironmentProfile,
)
from src.platform.security.configuration.service import (
    ConfigurationGovernanceService,
    ConfigValidator,
)

__all__ = [
    "ConfigScope",
    "ConfigStatus",
    "ChangeStatus",
    "ConfigVersion",
    "ConfigEntry",
    "EnvironmentProfile",
    "ChangeRequest",
    "ConfigValidator",
    "ConfigurationGovernanceService",
]
