"""Authentication manager (Module 3).

The façade that composes identity, credentials, sessions, verification and
recovery into the operations a caller actually performs: register a user, log
in, refresh, log out, verify an email, reset a password. It owns the repos for
the auth aggregate and enforces the password policy on every credential change.
"""

from __future__ import annotations

from src.platform.auth.identity import IdentityProvider, LocalIdentityProvider
from src.platform.auth.models import (
    Credential,
    Device,
    EmailVerification,
    RecoveryToken,
    RefreshToken,
    Session,
    User,
    UserStatus,
)
from src.platform.auth.passwords import PasswordHasher, PasswordPolicy
from src.platform.auth.recovery import AccountRecoveryService, EmailVerificationService
from src.platform.auth.sessions import IssuedSession, SessionManager
from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import ConflictError, PlatformValidationError
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository


class AuthenticationManager:
    """End-to-end authentication service for a platform deployment."""

    def __init__(
        self,
        *,
        policy: PasswordPolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.policy = policy or PasswordPolicy()
        self._hasher = PasswordHasher()

        # Auth aggregate repositories.
        self.users: InMemoryRepository[User] = InMemoryRepository("user")
        self.credentials: InMemoryRepository[Credential] = InMemoryRepository("credential")
        self.sessions_repo: InMemoryRepository[Session] = InMemoryRepository("session")
        self.refresh_repo: InMemoryRepository[RefreshToken] = InMemoryRepository("refresh_token")
        self.devices: InMemoryRepository[Device] = InMemoryRepository("device")
        self.verifications: InMemoryRepository[EmailVerification] = InMemoryRepository(
            "email_verification"
        )
        self.recovery_tokens: InMemoryRepository[RecoveryToken] = InMemoryRepository(
            "recovery_token"
        )

        # Collaborators.
        self.identity: IdentityProvider = LocalIdentityProvider(
            self.users, self.credentials, hasher=self._hasher
        )
        self.sessions = SessionManager(self.sessions_repo, self.refresh_repo, clock=self._clock)
        self.email_verification = EmailVerificationService(
            self.verifications, self.users, clock=self._clock
        )
        self.recovery = AccountRecoveryService(self.recovery_tokens, self.users, clock=self._clock)

    # -- registration -------------------------------------------------------

    def register_user(
        self,
        tenant_id: str,
        organization_id: str,
        email: str,
        password: str,
        *,
        display_name: str = "",
        activate: bool = True,
    ) -> User:
        """Create a user and set an initial password credential.

        Raises:
            ConflictError: If the email already exists in the tenant.
            PlatformValidationError: If the password fails the policy.
        """
        if self.identity.find_by_email(tenant_id, email) is not None:  # type: ignore[attr-defined]
            raise ConflictError(f"email '{email}' already registered")
        self.policy.validate(password)

        now = self._clock.now()
        user = User(
            id=generate_id("usr"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            email=email,
            display_name=display_name,
            status=UserStatus.ACTIVE if activate else UserStatus.INVITED,
            created_at=now,
            updated_at=now,
        )
        self.users.add(user)
        self._store_password(user, password)
        return user

    def _store_password(self, user: User, password: str) -> Credential:
        """Create/replace the user's credential (with history for reuse checks)."""
        salt, digest, iterations = self._hasher.hash(password)
        now = self._clock.now()
        existing = self.credentials.list(
            tenant_id=user.tenant_id, where=lambda c: c.user_id == user.id
        )
        if existing:
            cred = existing[0]
            # Store each past credential as "salt$hash$iterations" so a reuse
            # check can be verified against its *own* salt (not the new one).
            prior = f"{cred.salt}${cred.hash}${cred.iterations}"
            history = ([prior] + cred.previous_hashes)[: self.policy.history_size]
            cred.salt, cred.hash, cred.iterations = salt, digest, iterations
            cred.previous_hashes = history
            cred.rotated_at = now
            cred.touch(now)
            return self.credentials.update(cred)
        cred = Credential(
            id=generate_id("cred"),
            tenant_id=user.tenant_id,
            organization_id=user.organization_id,
            user_id=user.id,
            salt=salt,
            hash=digest,
            iterations=iterations,
            created_at=now,
            updated_at=now,
        )
        return self.credentials.add(cred)

    # -- login / logout -----------------------------------------------------

    def login(
        self,
        tenant_id: str,
        organization_id: str,
        email: str,
        password: str,
        *,
        remember_me: bool = False,
        device_id: str | None = None,
        ip_address: str = "",
    ) -> IssuedSession:
        """Authenticate and issue a session (+ refresh token)."""
        user = self.identity.authenticate(tenant_id, email, password)
        now = self._clock.now()
        user.last_login_at = now
        user.failed_login_count = 0
        user.touch(now)
        self.users.update(user)
        return self.sessions.issue(
            tenant_id,
            organization_id,
            user.id,
            device_id=device_id,
            remember_me=remember_me,
            ip_address=ip_address,
        )

    def logout(self, tenant_id: str, session_id: str) -> None:
        """Revoke a session (and its refresh tokens)."""
        self.sessions.revoke(tenant_id, session_id)

    def register_device(
        self, user: User, *, label: str, user_agent: str = "", ip_address: str = ""
    ) -> Device:
        """Register a device for a user (device-session tracking)."""
        now = self._clock.now()
        device = Device(
            id=generate_id("dev"),
            tenant_id=user.tenant_id,
            organization_id=user.organization_id,
            user_id=user.id,
            label=label,
            user_agent=user_agent,
            ip_address=ip_address,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        return self.devices.add(device)

    # -- credential lifecycle ----------------------------------------------

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Change a password after verifying the current one and the policy."""
        self.identity.authenticate(user.tenant_id, user.email, current_password)
        self._assert_new_password(user, new_password)
        self._store_password(user, new_password)
        # Force re-authentication everywhere on a credential change.
        self.sessions.revoke_all_for_user(user.tenant_id, user.id)

    def reset_password(self, tenant_id: str, token: str, new_password: str) -> User:
        """Complete an account-recovery flow by setting a new password."""
        rec = self.recovery.consume(tenant_id, token)
        user = self.users.require(rec.user_id, tenant_id=tenant_id)
        self._assert_new_password(user, new_password)
        self._store_password(user, new_password)
        self.sessions.revoke_all_for_user(tenant_id, user.id)
        return user

    def _assert_new_password(self, user: User, new_password: str) -> None:
        """Enforce policy and block reuse of a recent password."""
        self.policy.validate(new_password)
        existing = self.credentials.list(
            tenant_id=user.tenant_id, where=lambda c: c.user_id == user.id
        )
        if existing:
            cred = existing[0]
            # Current credential (verified against the current salt)...
            if cred.hash and self._hasher.verify(
                new_password,
                salt=cred.salt,
                expected=cred.hash,
                iterations=cred.iterations,
            ):
                raise PlatformValidationError("password was used recently")
            # ...plus each historical "salt$hash$iterations" entry.
            for entry in cred.previous_hashes:
                try:
                    old_salt, old_hash, old_iter = entry.split("$")
                except ValueError:
                    continue
                if self._hasher.verify(
                    new_password,
                    salt=old_salt,
                    expected=old_hash,
                    iterations=int(old_iter),
                ):
                    raise PlatformValidationError("password was used recently")
