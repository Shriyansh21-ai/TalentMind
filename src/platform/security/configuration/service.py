"""Configuration governance service (Module 11).

A versioned configuration registry with validation, an approval workflow,
change tracking, exact rollback and environment profiles — all tenant-isolated
and clock-driven. Validators are injectable per key; a change flows
propose → approve → apply, producing a new immutable version on apply.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.common.errors import ConfigurationGovernanceError
from src.platform.security.configuration.models import (
    ChangeRequest,
    ChangeStatus,
    ConfigEntry,
    ConfigScope,
    ConfigStatus,
    ConfigVersion,
    EnvironmentProfile,
)

#: A validator returns True if a proposed value is acceptable for a key.
ConfigValidator = Callable[[object], bool]


def _hash_value(value: object) -> str:
    try:
        serialized = json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        serialized = str(value)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


class ConfigurationGovernanceService:
    """Versioned config registry with validation, approval and rollback."""

    def __init__(self, *, require_approval: bool = True, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._require_approval = require_approval
        self.entries: InMemoryRepository[ConfigEntry] = InMemoryRepository("config_entry")
        self.changes: InMemoryRepository[ChangeRequest] = InMemoryRepository("config_change")
        self.profiles: InMemoryRepository[EnvironmentProfile] = InMemoryRepository("env_profile")
        self._validators: dict[str, ConfigValidator] = {}

    # -- registry -----------------------------------------------------------

    def register_validator(self, key: str, validator: ConfigValidator) -> None:
        """Register a validation function for a configuration key."""
        self._validators[key] = validator

    def _entry(self, tenant_id: str, key: str) -> ConfigEntry | None:
        found = self.entries.list(tenant_id=tenant_id, where=lambda e: e.key == key)
        return found[0] if found else None

    def set_initial(
        self,
        tenant_id: str,
        organization_id: str,
        key: str,
        value: object,
        *,
        scope: ConfigScope = ConfigScope.TENANT,
        author: str = "system",
    ) -> ConfigEntry:
        """Create a config entry with an initial ACTIVE version."""
        if self._entry(tenant_id, key) is not None:
            raise ConfigurationGovernanceError(f"config '{key}' already exists")
        self._validate(key, value)
        now = self._clock.now()
        entry = ConfigEntry(
            id=generate_id("cfg"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            key=key,
            scope=scope,
            status=ConfigStatus.ACTIVE,
            current_version=1,
            versions=[
                ConfigVersion(
                    version=1,
                    value=value,
                    author=author,
                    note="initial",
                    hash=_hash_value(value),
                    created_at=now,
                )
            ],
            created_at=now,
            updated_at=now,
        )
        return self.entries.add(entry)

    # -- change workflow ----------------------------------------------------

    def propose_change(
        self,
        tenant_id: str,
        organization_id: str,
        key: str,
        proposed_value: object,
        *,
        requested_by: str = "",
        note: str = "",
    ) -> ChangeRequest:
        """Propose a change to a config value (validated, awaiting approval)."""
        entry = self._entry(tenant_id, key)
        if entry is None:
            raise ConfigurationGovernanceError(f"config '{key}' not found")
        self._validate(key, proposed_value)
        now = self._clock.now()
        change = ChangeRequest(
            id=generate_id("chg"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            config_key=key,
            proposed_value=proposed_value,
            requested_by=requested_by,
            note=note,
            status=ChangeStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self.changes.add(change)
        entry.status = ConfigStatus.PENDING_APPROVAL
        self.entries.update(entry)
        if not self._require_approval:
            self.approve(tenant_id, change.id, approver="auto")
        return change

    def approve(self, tenant_id: str, change_id: str, *, approver: str) -> ConfigEntry:
        """Approve a change and apply it as a new immutable version."""
        change = self.changes.require(change_id, tenant_id=tenant_id)
        if change.status != ChangeStatus.PENDING:
            raise ConfigurationGovernanceError(f"change '{change_id}' is not pending")
        entry = self._entry(tenant_id, change.config_key)
        if entry is None:
            raise ConfigurationGovernanceError(f"config '{change.config_key}' not found")
        now = self._clock.now()
        new_version = entry.current_version + 1
        entry.versions.append(
            ConfigVersion(
                version=new_version,
                value=change.proposed_value,
                author=approver,
                note=change.note or "approved change",
                hash=_hash_value(change.proposed_value),
                created_at=now,
            )
        )
        entry.current_version = new_version
        entry.status = ConfigStatus.ACTIVE
        entry.touch(now)
        self.entries.update(entry)
        change.status = ChangeStatus.APPLIED
        change.approver = approver
        change.touch(now)
        self.changes.update(change)
        return entry

    def reject(self, tenant_id: str, change_id: str, *, approver: str) -> ChangeRequest:
        """Reject a pending change."""
        change = self.changes.require(change_id, tenant_id=tenant_id)
        change.status = ChangeStatus.REJECTED
        change.approver = approver
        change.touch(self._clock.now())
        entry = self._entry(tenant_id, change.config_key)
        if entry is not None:
            entry.status = ConfigStatus.ACTIVE
            self.entries.update(entry)
        return self.changes.update(change)

    def rollback(self, tenant_id: str, key: str, to_version: int) -> ConfigEntry:
        """Roll a config entry back to an earlier version (as a new version)."""
        entry = self._entry(tenant_id, key)
        if entry is None:
            raise ConfigurationGovernanceError(f"config '{key}' not found")
        target = next((v for v in entry.versions if v.version == to_version), None)
        if target is None:
            raise ConfigurationGovernanceError(f"version {to_version} not found for '{key}'")
        now = self._clock.now()
        new_version = entry.current_version + 1
        entry.versions.append(
            ConfigVersion(
                version=new_version,
                value=target.value,
                author="system",
                note=f"rollback to v{to_version}",
                hash=target.hash,
                created_at=now,
            )
        )
        entry.current_version = new_version
        entry.status = ConfigStatus.ROLLED_BACK
        entry.touch(now)
        return self.entries.update(entry)

    # -- environment profiles ----------------------------------------------

    def define_profile(
        self, tenant_id: str, organization_id: str, name: str, values: dict[str, object]
    ) -> EnvironmentProfile:
        """Define an environment profile (dev / staging / prod)."""
        now = self._clock.now()
        profile = EnvironmentProfile(
            id=generate_id("envp"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            values=values,
            created_at=now,
            updated_at=now,
        )
        return self.profiles.add(profile)

    # -- queries ------------------------------------------------------------

    def get(self, tenant_id: str, key: str) -> ConfigEntry:
        """Return a config entry (or raise)."""
        entry = self._entry(tenant_id, key)
        if entry is None:
            raise ConfigurationGovernanceError(f"config '{key}' not found")
        return entry

    def history(self, tenant_id: str, key: str) -> list[ConfigVersion]:
        """Return the version history of a config entry."""
        return list(self.get(tenant_id, key).versions)

    def pending_changes(self, tenant_id: str) -> list[ChangeRequest]:
        """Return pending change requests for a tenant."""
        return self.changes.list(
            tenant_id=tenant_id, where=lambda c: c.status == ChangeStatus.PENDING
        )

    def _validate(self, key: str, value: object) -> None:
        validator = self._validators.get(key)
        if validator is not None and not validator(value):
            raise ConfigurationGovernanceError(f"value for '{key}' failed validation")
