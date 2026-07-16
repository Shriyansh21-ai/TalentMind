"""Platform exception hierarchy.

A single, well-typed hierarchy so callers can catch broadly
(:class:`PlatformError`) or narrowly (e.g. :class:`TenantIsolationError`). This
is intentionally separate from the AI-platform ``AgentException`` hierarchy in
``src/ai/core/exceptions.py`` — no business-logic exceptions live here, only
enterprise-platform concerns.
"""

from __future__ import annotations


class PlatformError(Exception):
    """Base class for every enterprise-platform error.

    Attributes:
        message: Human-readable description.
        code: Stable machine-readable error code (used by the API layer).
    """

    code: str = "platform_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ConfigurationError(PlatformError):
    """Raised when the platform or a component is misconfigured."""

    code = "configuration_error"


class PlatformValidationError(PlatformError):
    """Raised when a value fails a platform invariant.

    Named ``Platform``-prefixed to avoid colliding with pydantic's
    ``ValidationError``.
    """

    code = "validation_error"


class NotFoundError(PlatformError):
    """Raised when a requested resource does not exist (within tenant scope)."""

    code = "not_found"


class ConflictError(PlatformError):
    """Raised on a uniqueness / state conflict (e.g. duplicate slug)."""

    code = "conflict"


class TenantIsolationError(PlatformError):
    """Raised when an operation would cross a tenant boundary.

    This is the platform's most important safety error: it fires whenever code
    attempts to read or write data belonging to a different tenant than the one
    in the active :class:`~src.platform.tenancy.context.TenantContext`.
    """

    code = "tenant_isolation_violation"


class AuthenticationError(PlatformError):
    """Raised when credentials are missing, invalid or expired."""

    code = "authentication_failed"


class SessionError(PlatformError):
    """Raised when a session is invalid, expired or revoked."""

    code = "session_invalid"


class PermissionDeniedError(PlatformError):
    """Raised when an authenticated principal lacks a required permission."""

    code = "permission_denied"


class QuotaExceededError(PlatformError):
    """Raised when a tenant exceeds a configured usage limit or seat count."""

    code = "quota_exceeded"


class FeatureDisabledError(PlatformError):
    """Raised when a gated feature is not enabled for the tenant/plan."""

    code = "feature_disabled"


class LicenseError(PlatformError):
    """Raised when a licensing constraint is violated."""

    code = "license_error"
