"""Identity manager (Module 1 — the identity control plane).

Owns the identity lifecycle (register → activate → suspend → deactivate),
authenticates local identities (salted PBKDF2 credential hashing — no plaintext
stored), issues clock-driven sessions + hashed tokens, and builds the runtime
:class:`IdentityContext`. Federated providers plug in through the registry; the
manager stays the single tenant-isolated entry point.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.common.errors import IdentityError
from src.platform.security.identity.models import (
    Identity,
    IdentityContext,
    IdentityMetadata,
    IdentityProviderType,
    IdentitySession,
    IdentityStatus,
    IdentityToken,
)
from src.platform.security.identity.providers import LocalIdentityProvider
from src.platform.security.identity.registry import IdentityProviderRegistry

_PBKDF2_ROUNDS = 120_000


def _hash_secret(secret: str, salt: bytes) -> str:
    """Return a hex PBKDF2-HMAC-SHA256 digest of ``secret`` with ``salt``."""
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, _PBKDF2_ROUNDS).hex()


class IdentityManager:
    """Register, authenticate and manage the lifecycle of identities."""

    def __init__(
        self,
        *,
        registry: IdentityProviderRegistry | None = None,
        identities: InMemoryRepository[Identity] | None = None,
        sessions: InMemoryRepository[IdentitySession] | None = None,
        token_ttl_seconds: int = 3600,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._ttl = token_ttl_seconds
        self.identities: InMemoryRepository[Identity] = identities or InMemoryRepository("identity")
        self.sessions: InMemoryRepository[IdentitySession] = sessions or InMemoryRepository(
            "identity_session"
        )
        # (salt_hex, hash_hex) keyed by identity id — credentials never in the model.
        self._credentials: dict[str, tuple[str, str]] = {}
        self.registry = registry or IdentityProviderRegistry()
        self.registry.register(LocalIdentityProvider(self._resolve))
        self.registry.register_future_providers()

    # -- lifecycle ----------------------------------------------------------

    def register_identity(
        self,
        tenant_id: str,
        organization_id: str,
        subject: str,
        *,
        secret: str = "",
        provider_type: IdentityProviderType = IdentityProviderType.LOCAL,
        email: str = "",
        display_name: str = "",
        roles: list[str] | None = None,
        groups: list[str] | None = None,
        status: IdentityStatus = IdentityStatus.ACTIVE,
    ) -> Identity:
        """Register a new identity (ACTIVE by default) for a tenant."""
        if self._resolve(tenant_id, subject) is not None:
            raise IdentityError(f"identity '{subject}' already exists for tenant")
        now = self._clock.now()
        identity = Identity(
            id=generate_id("idn"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            subject=subject,
            provider_type=provider_type,
            status=status,
            metadata=IdentityMetadata(display_name=display_name or subject, email=email),
            roles=roles or [],
            groups=groups or [],
            created_at=now,
            updated_at=now,
        )
        self.identities.add(identity)
        if provider_type == IdentityProviderType.LOCAL and secret:
            salt = os.urandom(16)
            self._credentials[identity.id] = (salt.hex(), _hash_secret(secret, salt))
        return identity

    def get(self, tenant_id: str, identity_id: str) -> Identity:
        """Return one identity (tenant-isolated)."""
        return self.identities.require(identity_id, tenant_id=tenant_id)

    def list(self, tenant_id: str) -> list[Identity]:
        """Return a tenant's identities."""
        return self.identities.list(tenant_id=tenant_id)

    def set_status(self, tenant_id: str, identity_id: str, status: IdentityStatus) -> Identity:
        """Transition an identity's lifecycle status."""
        identity = self.get(tenant_id, identity_id)
        identity.status = status
        identity.touch(self._clock.now())
        return self.identities.update(identity)

    def activate(self, tenant_id: str, identity_id: str) -> Identity:
        """Activate an identity."""
        return self.set_status(tenant_id, identity_id, IdentityStatus.ACTIVE)

    def suspend(self, tenant_id: str, identity_id: str) -> Identity:
        """Suspend an identity (cannot authenticate)."""
        return self.set_status(tenant_id, identity_id, IdentityStatus.SUSPENDED)

    def deactivate(self, tenant_id: str, identity_id: str) -> Identity:
        """Deactivate an identity and revoke its sessions."""
        for session in self.sessions.list(
            tenant_id=tenant_id, where=lambda s: s.identity_id == identity_id
        ):
            self.revoke_session(tenant_id, session.id)
        return self.set_status(tenant_id, identity_id, IdentityStatus.DEACTIVATED)

    # -- authentication -----------------------------------------------------

    def authenticate(
        self, tenant_id: str, subject: str, secret: str
    ) -> tuple[IdentityContext, str]:
        """Authenticate a local identity; return (context, plaintext_token).

        The plaintext token is returned exactly once. Unknown-subject and
        wrong-secret both raise the same error (resisting user enumeration).
        """
        identity = self._resolve(tenant_id, subject)
        # Always compute a hash to keep timing uniform.
        salt_hex, expected = self._credentials.get(
            identity.id if identity else "", (os.urandom(16).hex(), "")
        )
        candidate = _hash_secret(secret, bytes.fromhex(salt_hex))
        ok = bool(identity) and hmac.compare_digest(candidate, expected)
        if not ok or identity is None:
            raise IdentityError("invalid identity credentials", code="authentication_failed")
        if not identity.status.can_authenticate:
            raise IdentityError(
                f"identity is {identity.status.value}", code="authentication_failed"
            )

        now = self._clock.now()
        identity.last_authenticated_at = now
        self.identities.update(identity)

        plaintext = uuid.uuid4().hex + uuid.uuid4().hex
        from datetime import timedelta

        token = IdentityToken(
            token_hash=hashlib.sha256(plaintext.encode("utf-8")).hexdigest(),
            issued_at=now,
            expires_at=now + timedelta(seconds=self._ttl),
            claims={"sub": subject, "tenant": tenant_id},
        )
        session = IdentitySession(
            id=generate_id("sess"),
            tenant_id=tenant_id,
            organization_id=identity.organization_id,
            identity_id=identity.id,
            subject=subject,
            token=token,
            created_at=now,
            updated_at=now,
        )
        self.sessions.add(session)
        return self.build_context(identity, session), plaintext

    def validate_session(self, tenant_id: str, session_id: str) -> IdentitySession:
        """Return a valid session or raise if missing/expired/revoked."""
        session = self.sessions.require(session_id, tenant_id=tenant_id)
        if not session.is_valid_at(self._clock.now()):
            raise IdentityError("session invalid or expired", code="session_invalid")
        return session

    def revoke_session(self, tenant_id: str, session_id: str) -> IdentitySession:
        """Revoke a session."""
        session = self.sessions.require(session_id, tenant_id=tenant_id)
        session.active = False
        session.revoked_at = self._clock.now()
        session.touch(self._clock.now())
        return self.sessions.update(session)

    def build_context(self, identity: Identity, session: IdentitySession) -> IdentityContext:
        """Build the runtime :class:`IdentityContext` for an identity + session."""
        return IdentityContext(
            identity_id=identity.id,
            tenant_id=identity.tenant_id,
            subject=identity.subject,
            provider_type=identity.provider_type,
            roles=list(identity.roles),
            groups=list(identity.groups),
            attributes=dict(identity.metadata.attributes),
            session_id=session.id,
        )

    # -- internals ----------------------------------------------------------

    def _resolve(self, tenant_id: str, subject: str) -> Identity | None:
        matches = self.identities.list(tenant_id=tenant_id, where=lambda i: i.subject == subject)
        return matches[0] if matches else None
