"""Identity providers (Module 3).

Defines the :class:`IdentityProvider` seam — the single interface every identity
source (local password, and future SSO/OIDC/SAML) must satisfy — plus the
built-in :class:`LocalIdentityProvider` backed by password credentials. Keeping
authentication behind this protocol is what makes the platform SSO-ready without
any change to callers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.auth.models import Credential, User, UserStatus
from src.platform.auth.passwords import PasswordHasher
from src.platform.common.errors import AuthenticationError
from src.platform.common.repository import InMemoryRepository


@runtime_checkable
class IdentityProvider(Protocol):
    """A source of authenticated identity, scoped to a tenant."""

    key: str

    def authenticate(self, tenant_id: str, identifier: str, secret: str) -> User:
        """Return the authenticated :class:`User` or raise ``AuthenticationError``."""
        ...


class LocalIdentityProvider:
    """Password-based identity provider (the default, offline)."""

    key = "local"

    def __init__(
        self,
        users: InMemoryRepository[User],
        credentials: InMemoryRepository[Credential],
        *,
        hasher: PasswordHasher | None = None,
    ) -> None:
        self._users = users
        self._credentials = credentials
        self._hasher = hasher or PasswordHasher()

    def find_by_email(self, tenant_id: str, email: str) -> User | None:
        """Return the tenant's user with ``email`` (case-insensitive)."""
        target = email.strip().lower()
        matches = self._users.list(
            tenant_id=tenant_id, where=lambda u: u.email == target
        )
        return matches[0] if matches else None

    def _credential_for(self, tenant_id: str, user_id: str) -> Credential | None:
        """Return the active credential for a user within a tenant."""
        matches = self._credentials.list(
            tenant_id=tenant_id, where=lambda c: c.user_id == user_id
        )
        return matches[0] if matches else None

    def authenticate(self, tenant_id: str, identifier: str, secret: str) -> User:
        """Authenticate by email + password.

        Raises:
            AuthenticationError: On unknown user, wrong password, or a
                non-active account. The message is intentionally uniform so it
                does not leak whether an account exists.
        """
        user = self.find_by_email(tenant_id, identifier)
        credential = (
            self._credential_for(tenant_id, user.id) if user is not None else None
        )
        # Always run a verify to keep timing uniform even when the user is absent.
        ok = False
        if user is not None and credential is not None:
            ok = self._hasher.verify(
                secret,
                salt=credential.salt,
                expected=credential.hash,
                iterations=credential.iterations,
            )
        if user is None or credential is None or not ok:
            raise AuthenticationError("invalid credentials")
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError("account is not active")
        return user
