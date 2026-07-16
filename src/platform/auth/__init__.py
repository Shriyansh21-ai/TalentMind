"""Module 3 — Authentication.

An authentication *architecture* (not an OAuth integration): identity provider
seam, password policy + PBKDF2 hashing, session manager with rotating refresh
tokens and remember-me, device sessions, email verification and account
recovery — all offline and deterministic under an injected clock. The
:class:`AuthenticationManager` is the façade that composes them.
"""

from __future__ import annotations

from src.platform.auth.identity import IdentityProvider, LocalIdentityProvider
from src.platform.auth.manager import AuthenticationManager
from src.platform.auth.models import (
    Credential,
    Device,
    EmailVerification,
    RecoveryToken,
    RefreshToken,
    Session,
    SessionStatus,
    User,
    UserStatus,
)
from src.platform.auth.passwords import PasswordHasher, PasswordPolicy
from src.platform.auth.recovery import (
    AccountRecoveryService,
    EmailVerificationService,
)
from src.platform.auth.sessions import IssuedSession, SessionManager

__all__ = [
    "AuthenticationManager",
    "IdentityProvider",
    "LocalIdentityProvider",
    "PasswordPolicy",
    "PasswordHasher",
    "SessionManager",
    "IssuedSession",
    "EmailVerificationService",
    "AccountRecoveryService",
    "User",
    "UserStatus",
    "Credential",
    "Device",
    "Session",
    "SessionStatus",
    "RefreshToken",
    "EmailVerification",
    "RecoveryToken",
]
