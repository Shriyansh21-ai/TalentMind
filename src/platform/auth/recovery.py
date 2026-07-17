"""Email verification and account recovery (Module 3).

Single-use, time-boxed token flows for verifying an email address and resetting
a forgotten password. Tokens are stored only as SHA-256 hashes and returned in
plaintext exactly once (the caller is responsible for delivering them via the
notification framework — no email is actually sent here).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from src.platform.auth.models import EmailVerification, RecoveryToken, User
from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import PlatformValidationError
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository

_VERIFY_TTL = 24 * 3600
_RECOVERY_TTL = 3600


def _hash(token: str) -> str:
    """Return the SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class EmailVerificationService:
    """Issue and confirm email-verification challenges."""

    def __init__(
        self,
        verifications: InMemoryRepository[EmailVerification],
        users: InMemoryRepository[User],
        *,
        clock: Clock | None = None,
        ttl_seconds: int = _VERIFY_TTL,
    ) -> None:
        self._verifications = verifications
        self._users = users
        self._clock = clock or SystemClock()
        self._ttl = ttl_seconds

    def issue(self, user: User) -> str:
        """Create a verification challenge for ``user``; return the plaintext token."""
        now = self._clock.now()
        plain = secrets.token_urlsafe(24)
        self._verifications.add(
            EmailVerification(
                id=generate_id("emv"),
                tenant_id=user.tenant_id,
                organization_id=user.organization_id,
                user_id=user.id,
                token_hash=_hash(plain),
                expires_at=now + timedelta(seconds=self._ttl),
                created_at=now,
                updated_at=now,
            )
        )
        return plain

    def confirm(self, tenant_id: str, token: str) -> User:
        """Confirm a verification token and mark the user's email verified."""
        token_hash = _hash(token)
        matches = self._verifications.list(
            tenant_id=tenant_id, where=lambda v: v.token_hash == token_hash
        )
        if not matches:
            raise PlatformValidationError("invalid verification token")
        challenge = matches[0]
        now = self._clock.now()
        if challenge.verified_at is not None:
            raise PlatformValidationError("token already used")
        if challenge.expires_at is not None and now >= challenge.expires_at:
            raise PlatformValidationError("verification token expired")
        challenge.verified_at = now
        challenge.touch(now)
        self._verifications.update(challenge)
        user = self._users.require(challenge.user_id, tenant_id=tenant_id)
        user.email_verified = True
        user.touch(now)
        return self._users.update(user)


class AccountRecoveryService:
    """Issue and consume single-use password-reset tokens."""

    def __init__(
        self,
        recovery_tokens: InMemoryRepository[RecoveryToken],
        users: InMemoryRepository[User],
        *,
        clock: Clock | None = None,
        ttl_seconds: int = _RECOVERY_TTL,
    ) -> None:
        self._tokens = recovery_tokens
        self._users = users
        self._clock = clock or SystemClock()
        self._ttl = ttl_seconds

    def initiate(self, user: User) -> str:
        """Begin recovery for ``user``; return the single-use plaintext token."""
        now = self._clock.now()
        plain = secrets.token_urlsafe(24)
        self._tokens.add(
            RecoveryToken(
                id=generate_id("rec"),
                tenant_id=user.tenant_id,
                organization_id=user.organization_id,
                user_id=user.id,
                token_hash=_hash(plain),
                expires_at=now + timedelta(seconds=self._ttl),
                created_at=now,
                updated_at=now,
            )
        )
        return plain

    def consume(self, tenant_id: str, token: str) -> RecoveryToken:
        """Validate and mark a recovery token used; return it for the reset step."""
        token_hash = _hash(token)
        matches = self._tokens.list(tenant_id=tenant_id, where=lambda t: t.token_hash == token_hash)
        if not matches:
            raise PlatformValidationError("invalid recovery token")
        rec = matches[0]
        now = self._clock.now()
        if rec.used_at is not None:
            raise PlatformValidationError("recovery token already used")
        if rec.expires_at is not None and now >= rec.expires_at:
            raise PlatformValidationError("recovery token expired")
        rec.used_at = now
        rec.touch(now)
        return self._tokens.update(rec)
