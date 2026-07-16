"""Authentication domain models (Module 3).

Identity, credentials and session state. This is an authentication *architecture*
— it defines the entities and their lifecycle. No external identity providers or
OAuth integrations are implemented here; :class:`~src.platform.auth.identity`
defines the seam a future SSO/OIDC provider plugs into.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from src.platform.common.models import TenantScopedEntity

# Deliberately permissive email check: real address verification happens via the
# EmailVerification flow, not a regex. Avoids a hard email-validator dependency.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserStatus(str, Enum):
    """Lifecycle state of a user account."""

    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


class SessionStatus(str, Enum):
    """State of an authenticated session."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class User(TenantScopedEntity):
    """A user account within a tenant.

    Email is unique per tenant (enforced by the identity provider). Credentials
    live in a separate :class:`Credential` entity so the user record can be read
    and cached without ever touching secret material.
    """

    email: str
    display_name: str = ""
    status: UserStatus = UserStatus.INVITED
    email_verified: bool = False
    mfa_enabled: bool = False
    failed_login_count: int = 0
    last_login_at: datetime | None = None

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        """Lower-case and format-check the email address."""
        normalised = value.strip().lower()
        if not _EMAIL_RE.match(normalised):
            raise ValueError(f"invalid email address: {value!r}")
        return normalised

    def is_active(self) -> bool:
        """Return whether the account may authenticate."""
        return self.status == UserStatus.ACTIVE


class Credential(TenantScopedEntity):
    """A user's password credential (salted hash only — never plaintext)."""

    user_id: str
    algorithm: str = "pbkdf2_sha256"
    iterations: int = 240_000
    salt: str = ""
    hash: str = ""
    rotated_at: datetime | None = None
    previous_hashes: list[str] = Field(default_factory=list)


class Device(TenantScopedEntity):
    """A device from which a user has authenticated."""

    user_id: str
    label: str = "Unknown device"
    user_agent: str = ""
    ip_address: str = ""
    trusted: bool = False
    last_seen_at: datetime | None = None


class Session(TenantScopedEntity):
    """An authenticated session bound to a user (and optionally a device)."""

    user_id: str
    device_id: str | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    remember_me: bool = False
    token_hash: str = ""
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    last_seen_at: datetime | None = None
    ip_address: str = ""

    def is_active_at(self, moment: datetime) -> bool:
        """Return whether the session is valid (not revoked/expired) at ``moment``."""
        if self.status != SessionStatus.ACTIVE:
            return False
        return self.expires_at is None or moment < self.expires_at


class RefreshToken(TenantScopedEntity):
    """A rotating refresh token used to mint a new session token."""

    user_id: str
    session_id: str
    token_hash: str = ""
    expires_at: datetime | None = None
    used_at: datetime | None = None
    revoked: bool = False
    rotated_from: str | None = None


class EmailVerification(TenantScopedEntity):
    """A pending email-verification challenge."""

    user_id: str
    token_hash: str = ""
    expires_at: datetime | None = None
    verified_at: datetime | None = None


class RecoveryToken(TenantScopedEntity):
    """A single-use account-recovery (password reset) token."""

    user_id: str
    token_hash: str = ""
    expires_at: datetime | None = None
    used_at: datetime | None = None
