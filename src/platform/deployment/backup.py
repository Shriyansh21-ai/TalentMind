"""Backup & recovery framework (Module 6).

Interfaces plus an offline local reference for backing up configuration, cache,
logs, metadata and audit data, with recovery plans, restore validation and
recovery reports. **Interfaces only — no cloud storage.** A production
deployment binds a real :class:`BackupProvider` (S3/GCS/Azure/tape) behind the
same seam; the local provider keeps deterministic in-memory snapshots for tests.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import Entity, PlatformModel
from src.platform.deployment.common.errors import BackupError


class BackupType(str, Enum):
    """What a backup captures."""

    CONFIGURATION = "configuration"
    CACHE = "cache"
    LOGS = "logs"
    METADATA = "metadata"
    AUDIT = "audit"


class BackupManifest(Entity):
    """Non-secret metadata describing a backup (not the bytes)."""

    backup_type: BackupType
    location: str = ""  # provider-relative reference, never a secret
    size_bytes: int = 0
    checksum: str = ""
    item_count: int = 0


@runtime_checkable
class BackupProvider(Protocol):
    """A backup storage backend seam (interface only)."""

    name: str

    def put(self, key: str, payload: bytes) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


class LocalBackupProvider:
    """An offline, in-memory backup provider (deterministic reference)."""

    name = "local"

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put(self, key: str, payload: bytes) -> None:
        self._store[key] = bytes(payload)

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def exists(self, key: str) -> bool:
        return key in self._store

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class RecoveryPlan(Entity):
    """An ordered recovery plan with RTO/RPO objectives."""

    name: str
    rto_minutes: int = 60  # recovery time objective
    rpo_minutes: int = 15  # recovery point objective
    steps: list[str] = Field(default_factory=list)


class RestoreValidation(PlatformModel):
    """The result of validating a restore against its manifest."""

    manifest_id: str
    valid: bool = False
    reason: str = ""


class RecoveryReport(PlatformModel):
    """A summary of a recovery drill / operation."""

    plan_name: str
    restored_types: list[str] = Field(default_factory=list)
    all_valid: bool = True
    validations: list[RestoreValidation] = Field(default_factory=list)


class BackupManager:
    """Creates backups, plans recovery and validates restores (offline)."""

    def __init__(
        self,
        provider: BackupProvider | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.provider: BackupProvider = provider or LocalBackupProvider()
        self._manifests: dict[str, BackupManifest] = {}

    # -- backup -------------------------------------------------------------

    def backup(self, backup_type: BackupType, data: object) -> BackupManifest:
        """Serialize ``data`` and store it, returning a manifest."""
        payload = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        checksum = hashlib.sha256(payload).hexdigest()
        now = self._clock.now()
        manifest_id = generate_id("bkp")
        key = f"{backup_type.value}/{manifest_id}"
        self.provider.put(key, payload)
        manifest = BackupManifest(
            id=manifest_id, backup_type=backup_type, location=key,
            size_bytes=len(payload), checksum=checksum,
            item_count=len(data) if hasattr(data, "__len__") else 1,
            created_at=now, updated_at=now,
        )
        self._manifests[manifest_id] = manifest
        return manifest

    def manifests(self, *, backup_type: BackupType | None = None) -> list[BackupManifest]:
        """Return backup manifests, optionally filtered by type."""
        result = list(self._manifests.values())
        if backup_type is not None:
            result = [m for m in result if m.backup_type == backup_type]
        return result

    # -- restore ------------------------------------------------------------

    def validate_restore(self, manifest_id: str) -> RestoreValidation:
        """Verify a stored backup matches its manifest checksum."""
        manifest = self._manifests.get(manifest_id)
        if manifest is None:
            return RestoreValidation(manifest_id=manifest_id, valid=False, reason="unknown manifest")
        payload = self.provider.get(manifest.location)
        if payload is None:
            return RestoreValidation(manifest_id=manifest_id, valid=False, reason="backup missing")
        actual = hashlib.sha256(payload).hexdigest()
        if actual != manifest.checksum:
            return RestoreValidation(manifest_id=manifest_id, valid=False, reason="checksum mismatch")
        return RestoreValidation(manifest_id=manifest_id, valid=True, reason="ok")

    def restore(self, manifest_id: str) -> object:
        """Return the deserialized data for a valid backup, or raise."""
        validation = self.validate_restore(manifest_id)
        if not validation.valid:
            raise BackupError(f"restore validation failed: {validation.reason}")
        manifest = self._manifests[manifest_id]
        payload = self.provider.get(manifest.location)
        assert payload is not None
        return json.loads(payload.decode("utf-8"))

    # -- recovery -----------------------------------------------------------

    def recovery_plan(self, name: str = "default") -> RecoveryPlan:
        """Return a standard recovery plan (RTO/RPO + ordered steps)."""
        now = self._clock.now()
        return RecoveryPlan(
            id=generate_id("rec"), name=name, rto_minutes=60, rpo_minutes=15,
            steps=[
                "Declare incident and assemble recovery team",
                "Restore latest configuration backup",
                "Restore metadata and audit backups",
                "Warm caches from backup or rebuild",
                "Validate restores against manifests",
                "Run production readiness validation",
                "Resume traffic and monitor",
            ],
            created_at=now, updated_at=now,
        )

    def recovery_report(self, plan_name: str = "default") -> RecoveryReport:
        """Validate every known backup and produce a recovery report."""
        validations = [self.validate_restore(mid) for mid in self._manifests]
        return RecoveryReport(
            plan_name=plan_name,
            restored_types=sorted({m.backup_type.value for m in self._manifests.values()}),
            all_valid=all(v.valid for v in validations) if validations else True,
            validations=validations,
        )
