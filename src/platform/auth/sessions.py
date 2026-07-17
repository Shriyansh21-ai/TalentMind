"""Session management (Module 3).

Issues, validates, refreshes and revokes sessions and their rotating refresh
tokens. Session tokens are returned to the caller in plaintext exactly once and
stored only as SHA-256 hashes, so a dump of the session store never yields a
usable token. Expiration is driven by the injected :class:`Clock`, so tests can
fast-forward time deterministically.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from src.platform.auth.models import (
    RefreshToken,
    Session,
    SessionStatus,
)
from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import SessionError
from src.platform.common.ids import generate_id
from src.platform.common.models import PlatformModel
from src.platform.common.repository import InMemoryRepository

# Default session lifetimes (seconds). "Remember me" extends the session TTL.
_DEFAULT_TTL = 8 * 3600
_REMEMBER_TTL = 30 * 86400
_REFRESH_TTL = 30 * 86400


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a bearer token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class IssuedSession(PlatformModel):
    """A freshly-issued session plus its one-time plaintext secrets."""

    session: Session
    session_token: str
    refresh_token: str


class SessionManager:
    """Create and manage authenticated sessions and refresh tokens."""

    def __init__(
        self,
        sessions: InMemoryRepository[Session],
        refresh_tokens: InMemoryRepository[RefreshToken],
        *,
        clock: Clock | None = None,
        default_ttl_seconds: int = _DEFAULT_TTL,
        remember_ttl_seconds: int = _REMEMBER_TTL,
        refresh_ttl_seconds: int = _REFRESH_TTL,
    ) -> None:
        self._sessions = sessions
        self._refresh = refresh_tokens
        self._clock = clock or SystemClock()
        self._default_ttl = default_ttl_seconds
        self._remember_ttl = remember_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds

    # -- issuing ------------------------------------------------------------

    def issue(
        self,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        *,
        device_id: str | None = None,
        remember_me: bool = False,
        ip_address: str = "",
    ) -> IssuedSession:
        """Create a new active session and its first refresh token."""
        now = self._clock.now()
        ttl = self._remember_ttl if remember_me else self._default_ttl
        token = secrets.token_urlsafe(32)
        session = Session(
            id=generate_id("sess"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            user_id=user_id,
            device_id=device_id,
            status=SessionStatus.ACTIVE,
            remember_me=remember_me,
            token_hash=_hash_token(token),
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl),
            last_seen_at=now,
            ip_address=ip_address,
            created_at=now,
            updated_at=now,
        )
        self._sessions.add(session)
        refresh_plain = self._issue_refresh(session)
        return IssuedSession(session=session, session_token=token, refresh_token=refresh_plain)

    def _issue_refresh(self, session: Session, rotated_from: str | None = None) -> str:
        """Mint a refresh token for ``session`` and return its plaintext value."""
        now = self._clock.now()
        plain = secrets.token_urlsafe(32)
        token = RefreshToken(
            id=generate_id("rt"),
            tenant_id=session.tenant_id,
            organization_id=session.organization_id,
            user_id=session.user_id,
            session_id=session.id,
            token_hash=_hash_token(plain),
            expires_at=now + timedelta(seconds=self._refresh_ttl),
            rotated_from=rotated_from,
            created_at=now,
            updated_at=now,
        )
        self._refresh.add(token)
        return plain

    # -- validating ---------------------------------------------------------

    def validate(self, tenant_id: str, session_token: str) -> Session:
        """Return the active session for ``session_token`` or raise.

        Also lazily marks an expired session as ``EXPIRED`` so its state is
        accurate in the store.
        """
        token_hash = _hash_token(session_token)
        matches = self._sessions.list(
            tenant_id=tenant_id, where=lambda s: s.token_hash == token_hash
        )
        if not matches:
            raise SessionError("session not found")
        session = matches[0]
        now = self._clock.now()
        if session.status == SessionStatus.ACTIVE and not session.is_active_at(now):
            session.status = SessionStatus.EXPIRED
            session.touch(now)
            self._sessions.update(session)
        if not session.is_active_at(now):
            raise SessionError(f"session is {session.status.value}")
        session.last_seen_at = now
        self._sessions.update(session)
        return session

    # -- refreshing ---------------------------------------------------------

    def refresh(self, tenant_id: str, refresh_token: str) -> IssuedSession:
        """Rotate a refresh token, issuing a new session token.

        The presented refresh token is single-use: it is marked used and a new
        refresh token is minted (rotation), mitigating token replay.
        """
        token_hash = _hash_token(refresh_token)
        matches = self._refresh.list(
            tenant_id=tenant_id, where=lambda t: t.token_hash == token_hash
        )
        if not matches:
            raise SessionError("refresh token not found")
        token = matches[0]
        now = self._clock.now()
        if token.revoked or token.used_at is not None:
            raise SessionError("refresh token already used or revoked")
        if token.expires_at is not None and now >= token.expires_at:
            raise SessionError("refresh token expired")

        session = self._sessions.require(token.session_id, tenant_id=tenant_id)
        if session.status != SessionStatus.ACTIVE:
            raise SessionError(f"session is {session.status.value}")

        # Consume the old token and rotate a new session token + refresh token.
        token.used_at = now
        token.touch(now)
        self._refresh.update(token)

        new_session_token = secrets.token_urlsafe(32)
        ttl = self._remember_ttl if session.remember_me else self._default_ttl
        session.token_hash = _hash_token(new_session_token)
        session.expires_at = now + timedelta(seconds=ttl)
        session.last_seen_at = now
        session.touch(now)
        self._sessions.update(session)

        new_refresh = self._issue_refresh(session, rotated_from=token.id)
        return IssuedSession(
            session=session,
            session_token=new_session_token,
            refresh_token=new_refresh,
        )

    # -- revoking -----------------------------------------------------------

    def revoke(self, tenant_id: str, session_id: str) -> None:
        """Revoke a session and all of its refresh tokens."""
        session = self._sessions.get(session_id, tenant_id=tenant_id)
        if session is None:
            return
        now = self._clock.now()
        session.status = SessionStatus.REVOKED
        session.touch(now)
        self._sessions.update(session)
        for token in self._refresh.list(
            tenant_id=tenant_id, where=lambda t: t.session_id == session_id
        ):
            token.revoked = True
            token.touch(now)
            self._refresh.update(token)

    def revoke_all_for_user(self, tenant_id: str, user_id: str) -> int:
        """Revoke every active session for a user; return the count revoked."""
        active = self._sessions.list(
            tenant_id=tenant_id,
            where=lambda s: s.user_id == user_id and s.status == SessionStatus.ACTIVE,
        )
        for session in active:
            self.revoke(tenant_id, session.id)
        return len(active)

    def active_sessions(self, tenant_id: str, user_id: str) -> list[Session]:
        """Return a user's currently-active sessions (device session list)."""
        now = self._clock.now()
        return self._sessions.list(
            tenant_id=tenant_id,
            where=lambda s: s.user_id == user_id and s.is_active_at(now),
        )
