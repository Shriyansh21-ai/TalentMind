"""Connection secrets & credential abstraction (Module 14 — Security).

Enterprise integrations need credentials (OAuth tokens, API keys, service
accounts) — but the platform must **never** persist a plaintext secret. This
module defines:

* :class:`SecretProvider` — the seam every real secret backend (HashiCorp Vault,
  AWS Secrets Manager, Azure Key Vault) satisfies.
* :class:`InMemorySecretProvider` — an offline reference that stores secrets
  **obfuscated** (never in clear) and is tenant-namespaced so one tenant can
  never read another's secret.
* :class:`CredentialVault` — a thin service over a provider that mints opaque
  credential references, handles token lifecycle (issue / rotate / expire) and
  redacts values on read.
* :class:`EncryptionProvider` — an interface a future KMS binds to.

No real cryptography or network calls are performed; obfuscation here is a
reversible reference stand-in for a real KMS/Vault, chosen so that a plaintext
secret is never stored verbatim and never logged.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import PlatformModel
from src.platform.integrations.common.errors import CredentialError
from src.platform.tenancy.isolation import TenantIsolationGuard


class CredentialType(str, Enum):
    """The kind of credential material a secret holds."""

    OAUTH2_TOKEN = "oauth2_token"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    SERVICE_ACCOUNT = "service_account"
    CERTIFICATE = "certificate"


class SecretRef(PlatformModel):
    """An opaque, non-secret reference the platform stores in place of a value.

    The reference is safe to persist and display; resolving it back to a value
    requires the owning tenant *and* the :class:`SecretProvider`.
    """

    ref: str
    tenant_id: str
    credential_type: CredentialType = CredentialType.API_KEY
    created_at: datetime = Field(default_factory=lambda: datetime.min)
    expires_at: datetime | None = None
    rotated_at: datetime | None = None

    def is_expired(self, now: datetime) -> bool:
        """Return whether the referenced credential has expired at ``now``."""
        return self.expires_at is not None and now >= self.expires_at


@runtime_checkable
class EncryptionProvider(Protocol):
    """A reversible transform seam a future KMS/HSM binds to."""

    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...


class Base64ObfuscationProvider:
    """Offline reference "encryption" — reversible base64 obfuscation.

    This is **not** cryptography; it exists so the in-memory reference never
    stores a plaintext secret verbatim. A production deployment binds a real
    :class:`EncryptionProvider` (KMS envelope encryption) at this seam.
    """

    def encrypt(self, plaintext: str) -> str:
        """Return an obfuscated form of ``plaintext``."""
        return base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """Reverse :meth:`encrypt`."""
        return base64.b64decode(ciphertext.encode("ascii")).decode("utf-8")


@runtime_checkable
class SecretProvider(Protocol):
    """A tenant-namespaced secret backend (interface only)."""

    name: str

    def store(self, tenant_id: str, ref: str, value: str) -> None: ...
    def read(self, tenant_id: str, ref: str) -> str | None: ...
    def delete(self, tenant_id: str, ref: str) -> None: ...
    def exists(self, tenant_id: str, ref: str) -> bool: ...


class InMemorySecretProvider:
    """Offline, tenant-namespaced secret store (obfuscated, never plaintext).

    Keys are namespaced by tenant via
    :meth:`~src.platform.tenancy.isolation.TenantIsolationGuard.namespaced_key`,
    so a lookup can never return another tenant's secret.
    """

    def __init__(
        self,
        name: str = "memory-vault",
        *,
        encryption: EncryptionProvider | None = None,
    ) -> None:
        self.name = name
        self._encryption = encryption or Base64ObfuscationProvider()
        self._store: dict[str, str] = {}

    def store(self, tenant_id: str, ref: str, value: str) -> None:
        """Persist ``value`` (obfuscated) under a tenant-namespaced reference."""
        key = TenantIsolationGuard.namespaced_key(tenant_id, ref)
        self._store[key] = self._encryption.encrypt(value)

    def read(self, tenant_id: str, ref: str) -> str | None:
        """Return the plaintext value for a tenant's ``ref`` (or ``None``)."""
        key = TenantIsolationGuard.namespaced_key(tenant_id, ref)
        stored = self._store.get(key)
        return None if stored is None else self._encryption.decrypt(stored)

    def delete(self, tenant_id: str, ref: str) -> None:
        """Remove a tenant's secret (no-op if absent)."""
        self._store.pop(TenantIsolationGuard.namespaced_key(tenant_id, ref), None)

    def exists(self, tenant_id: str, ref: str) -> bool:
        """Return whether a tenant has a secret at ``ref``."""
        return TenantIsolationGuard.namespaced_key(tenant_id, ref) in self._store


class VaultSecretProvider:
    """Placeholder for a future HashiCorp Vault / cloud KMS backend.

    Present so wiring can target the real seam today; every method intentionally
    signals it is not yet implemented rather than silently succeeding.
    """

    name = "vault"

    def _not_ready(self) -> CredentialError:
        return CredentialError(
            "VaultSecretProvider is an architecture placeholder; bind a real backend before use",
            code="secret_provider_not_configured",
        )

    def store(self, tenant_id: str, ref: str, value: str) -> None:
        raise self._not_ready()

    def read(self, tenant_id: str, ref: str) -> str | None:
        raise self._not_ready()

    def delete(self, tenant_id: str, ref: str) -> None:
        raise self._not_ready()

    def exists(self, tenant_id: str, ref: str) -> bool:
        raise self._not_ready()


class CredentialVault:
    """Mints credential references and manages their lifecycle.

    Callers hand a plaintext secret to :meth:`issue` and receive back an opaque
    :class:`SecretRef`. The plaintext is stored only through the injected
    :class:`SecretProvider` (obfuscated); the vault itself keeps only references
    and metadata. Reads return a redacted preview by default — the raw value is
    only produced by :meth:`resolve`, and never logged.
    """

    def __init__(
        self,
        provider: SecretProvider | None = None,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._provider = provider or InMemorySecretProvider()
        self._clock = clock or SystemClock()
        self._refs: dict[str, SecretRef] = {}

    def issue(
        self,
        tenant_id: str,
        value: str,
        *,
        credential_type: CredentialType = CredentialType.API_KEY,
        ttl_seconds: int | None = None,
    ) -> SecretRef:
        """Store ``value`` and return an opaque reference to it."""
        if not value:
            raise CredentialError("cannot issue an empty credential")
        now = self._clock.now()
        ref_id = generate_id("cred")
        self._provider.store(tenant_id, ref_id, value)
        secret_ref = SecretRef(
            ref=ref_id,
            tenant_id=tenant_id,
            credential_type=credential_type,
            created_at=now,
            expires_at=(now + timedelta(seconds=ttl_seconds)) if ttl_seconds else None,
        )
        self._refs[ref_id] = secret_ref
        return secret_ref

    def rotate(self, tenant_id: str, ref: str, value: str) -> SecretRef:
        """Replace the value behind ``ref`` and stamp ``rotated_at``."""
        secret_ref = self._require(tenant_id, ref)
        self._provider.store(tenant_id, ref, value)
        secret_ref.rotated_at = self._clock.now()
        return secret_ref

    def resolve(self, tenant_id: str, ref: str) -> str:
        """Return the raw secret value (used only at the point of use)."""
        secret_ref = self._require(tenant_id, ref)
        if secret_ref.is_expired(self._clock.now()):
            raise CredentialError(f"credential '{ref}' has expired")
        value = self._provider.read(tenant_id, ref)
        if value is None:
            raise CredentialError(f"credential '{ref}' not found")
        return value

    def redacted(self, tenant_id: str, ref: str) -> str:
        """Return a display-safe, redacted preview of a credential."""
        try:
            value = self.resolve(tenant_id, ref)
        except CredentialError:
            return "••••"
        if len(value) <= 4:
            return "••••"
        return f"••••{value[-4:]}"

    def revoke(self, tenant_id: str, ref: str) -> None:
        """Delete a credential and forget its reference."""
        self._provider.delete(tenant_id, ref)
        self._refs.pop(ref, None)

    def describe(self, ref: str) -> SecretRef | None:
        """Return the (non-secret) metadata for a reference."""
        return self._refs.get(ref)

    def _require(self, tenant_id: str, ref: str) -> SecretRef:
        secret_ref = self._refs.get(ref)
        if secret_ref is None:
            raise CredentialError(f"credential '{ref}' not found")
        if secret_ref.tenant_id != tenant_id:
            raise CredentialError("cross-tenant credential access denied")
        return secret_ref
