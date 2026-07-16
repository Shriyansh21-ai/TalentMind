"""Password policy and hashing (Module 3).

Offline, stdlib-only password handling: PBKDF2-HMAC-SHA256 with a per-credential
random salt and a constant-time comparison. No plaintext password is ever
stored or logged. :class:`PasswordPolicy` is a declarative strength policy the
:class:`AuthenticationManager` enforces on registration and reset.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from src.platform.common.errors import PlatformValidationError
from src.platform.common.models import PlatformModel

_ALGORITHM = "pbkdf2_sha256"
_DEFAULT_ITERATIONS = 240_000


class PasswordPolicy(PlatformModel):
    """Declarative password-strength requirements."""

    min_length: int = 12
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True
    require_symbol: bool = True
    max_age_days: int | None = 180
    history_size: int = 5

    def violations(self, password: str) -> list[str]:
        """Return a list of human-readable policy violations (empty if valid)."""
        problems: list[str] = []
        if len(password) < self.min_length:
            problems.append(f"must be at least {self.min_length} characters")
        if self.require_upper and not any(c.isupper() for c in password):
            problems.append("must contain an uppercase letter")
        if self.require_lower and not any(c.islower() for c in password):
            problems.append("must contain a lowercase letter")
        if self.require_digit and not any(c.isdigit() for c in password):
            problems.append("must contain a digit")
        if self.require_symbol and password.isalnum():
            problems.append("must contain a symbol")
        return problems

    def validate(self, password: str) -> None:
        """Raise :class:`PlatformValidationError` if ``password`` is too weak."""
        problems = self.violations(password)
        if problems:
            raise PlatformValidationError("password policy: " + "; ".join(problems))


class PasswordHasher:
    """Hash and verify passwords with PBKDF2-HMAC-SHA256."""

    def __init__(self, iterations: int = _DEFAULT_ITERATIONS) -> None:
        self.iterations = iterations
        self.algorithm = _ALGORITHM

    def hash(self, password: str) -> tuple[str, str, int]:
        """Return ``(salt_hex, hash_hex, iterations)`` for ``password``."""
        salt = secrets.token_hex(16)
        digest = self._derive(password, salt, self.iterations)
        return salt, digest, self.iterations

    def verify(self, password: str, *, salt: str, expected: str, iterations: int) -> bool:
        """Return whether ``password`` matches, in constant time."""
        if not salt or not expected:
            return False
        candidate = self._derive(password, salt, iterations)
        return hmac.compare_digest(candidate, expected)

    @staticmethod
    def _derive(password: str, salt: str, iterations: int) -> str:
        """Derive the PBKDF2 digest as a hex string."""
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
        )
        return dk.hex()
