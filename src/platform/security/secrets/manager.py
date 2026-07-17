"""Secret manager (Module 4).

Stores secrets through a swappable :class:`SecretProvider` (obfuscated, never
plaintext), tracks per-secret metadata (version, expiration, rotation schedule,
access count) and enforces rotation/expiration policies — all tenant-namespaced.
The raw value is only produced by :meth:`reveal` at the point of use and is
never logged; everything else returns redacted previews.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import TenantScopedEntity
from src.platform.security.common.errors import SecretError
from src.platform.security.secrets.providers import LocalSecretProvider, SecretProvider


class SecretStatus(str, Enum):
    """The lifecycle state of a stored secret."""

    ACTIVE = "active"
    EXPIRED = "expired"
    ROTATION_DUE = "rotation_due"
    REVOKED = "revoked"


class SecretMetadata(TenantScopedEntity):
    """Non-secret metadata about a stored secret (never holds the value)."""

    name: str
    ref: str
    version: int = 1
    expires_at: datetime | None = None
    rotation_interval_days: int | None = None
    last_rotated_at: datetime | None = None
    access_count: int = 0
    last_accessed_at: datetime | None = None
    revoked: bool = False

    def status_at(self, moment: datetime) -> SecretStatus:
        """Return the secret's status at ``moment``."""
        if self.revoked:
            return SecretStatus.REVOKED
        if self.expires_at is not None and moment >= self.expires_at:
            return SecretStatus.EXPIRED
        if self.rotation_interval_days is not None and self.last_rotated_at is not None:
            due = self.last_rotated_at + timedelta(days=self.rotation_interval_days)
            if moment >= due:
                return SecretStatus.ROTATION_DUE
        return SecretStatus.ACTIVE


class AccessRecord(TenantScopedEntity):
    """An access-tracking record for secret reads (audit trail)."""

    secret_ref: str
    accessor: str = ""
    at: datetime | None = None


class SecretManager:
    """Manages secret storage, metadata, rotation, expiration and access."""

    def __init__(
        self,
        provider: SecretProvider | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.provider: SecretProvider = provider or LocalSecretProvider()
        self._metadata: dict[str, SecretMetadata] = {}
        self._access_log: list[AccessRecord] = []

    # -- storage ------------------------------------------------------------

    def store(
        self,
        tenant_id: str,
        organization_id: str,
        name: str,
        value: str,
        *,
        ttl_seconds: int | None = None,
        rotation_interval_days: int | None = None,
    ) -> SecretMetadata:
        """Store a secret and return its (non-secret) metadata."""
        if not value:
            raise SecretError("cannot store an empty secret")
        now = self._clock.now()
        ref = generate_id("sec")
        self.provider.store(tenant_id, ref, value)
        meta = SecretMetadata(
            id=generate_id("secmeta"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            name=name,
            ref=ref,
            expires_at=(now + timedelta(seconds=ttl_seconds)) if ttl_seconds else None,
            rotation_interval_days=rotation_interval_days,
            last_rotated_at=now,
            created_at=now,
            updated_at=now,
        )
        self._metadata[ref] = meta
        return meta

    def rotate(self, tenant_id: str, ref: str, new_value: str) -> SecretMetadata:
        """Replace a secret's value and bump its version/rotation timestamp."""
        meta = self._require(tenant_id, ref)
        self.provider.store(tenant_id, ref, new_value)
        meta.version += 1
        meta.last_rotated_at = self._clock.now()
        meta.touch(meta.last_rotated_at)
        return meta

    def reveal(self, tenant_id: str, ref: str, *, accessor: str = "system") -> str:
        """Return the raw secret value (point-of-use only), tracking access."""
        meta = self._require(tenant_id, ref)
        now = self._clock.now()
        status = meta.status_at(now)
        if status in (SecretStatus.EXPIRED, SecretStatus.REVOKED):
            raise SecretError(f"secret '{meta.name}' is {status.value}")
        value = self.provider.read(tenant_id, ref)
        if value is None:
            raise SecretError(f"secret '{ref}' not found")
        meta.access_count += 1
        meta.last_accessed_at = now
        self._access_log.append(
            AccessRecord(
                id=generate_id("secacc"),
                tenant_id=tenant_id,
                organization_id=meta.organization_id,
                secret_ref=ref,
                accessor=accessor,
                at=now,
                created_at=now,
                updated_at=now,
            )
        )
        return value

    def redacted(self, tenant_id: str, ref: str) -> str:
        """Return a display-safe, redacted preview of a secret."""
        try:
            value = self.provider.read(tenant_id, ref)
        except Exception:
            value = None
        if not value or len(value) <= 4:
            return "••••"
        return f"••••{value[-4:]}"

    def revoke(self, tenant_id: str, ref: str) -> SecretMetadata:
        """Revoke a secret (deletes the value, marks metadata revoked)."""
        meta = self._require(tenant_id, ref)
        self.provider.delete(tenant_id, ref)
        meta.revoked = True
        meta.touch(self._clock.now())
        return meta

    # -- queries ------------------------------------------------------------

    def metadata(self, tenant_id: str) -> list[SecretMetadata]:
        """Return a tenant's secret metadata (never values)."""
        return [m for m in self._metadata.values() if m.tenant_id == tenant_id]

    def rotation_due(self, tenant_id: str) -> list[SecretMetadata]:
        """Return secrets whose rotation window has elapsed."""
        now = self._clock.now()
        return [
            m for m in self.metadata(tenant_id) if m.status_at(now) == SecretStatus.ROTATION_DUE
        ]

    def access_log(self, tenant_id: str) -> list[AccessRecord]:
        """Return the tenant's secret-access records."""
        return [r for r in self._access_log if r.tenant_id == tenant_id]

    def _require(self, tenant_id: str, ref: str) -> SecretMetadata:
        meta = self._metadata.get(ref)
        if meta is None or meta.tenant_id != tenant_id:
            raise SecretError(f"secret '{ref}' not found")
        return meta
