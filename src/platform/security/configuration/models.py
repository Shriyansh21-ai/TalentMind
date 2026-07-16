"""Configuration governance models (Module 11).

Versioned, tenant-scoped configuration entries with an approval workflow, change
requests, and environment profiles. Every value change produces an immutable
:class:`ConfigVersion` (hashed), so history is complete and rollback is exact.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity


class ConfigScope(str, Enum):
    """The scope a configuration entry applies to."""

    PLATFORM = "platform"
    TENANT = "tenant"
    RUNTIME = "runtime"


class ConfigStatus(str, Enum):
    """The lifecycle state of a configuration entry."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"


class ChangeStatus(str, Enum):
    """The state of a configuration change request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class ConfigVersion(PlatformModel):
    """An immutable version of a configuration value."""

    version: int
    value: object = None
    author: str = ""
    note: str = ""
    hash: str = ""
    created_at: datetime | None = None


class ConfigEntry(TenantScopedEntity):
    """A versioned configuration entry."""

    key: str
    scope: ConfigScope = ConfigScope.TENANT
    status: ConfigStatus = ConfigStatus.ACTIVE
    current_version: int = 1
    versions: list[ConfigVersion] = Field(default_factory=list)

    @property
    def current_value(self) -> object:
        """Return the value of the current version."""
        for v in self.versions:
            if v.version == self.current_version:
                return v.value
        return None


class EnvironmentProfile(TenantScopedEntity):
    """A named environment profile (dev / staging / prod) of config values."""

    name: str
    values: dict[str, object] = Field(default_factory=dict)


class ChangeRequest(TenantScopedEntity):
    """A proposed configuration change awaiting approval."""

    config_key: str
    proposed_value: object = None
    requested_by: str = ""
    status: ChangeStatus = ChangeStatus.PENDING
    approver: str = ""
    note: str = ""
