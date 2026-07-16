"""API error standards (Module 10).

Maps the platform exception hierarchy onto stable HTTP statuses + error codes so
the future REST layer can translate any :class:`PlatformError` into a consistent
:class:`ApiResponse` without endpoint-specific handling.
"""

from __future__ import annotations

from src.platform.api.responses import ApiResponse, ResponseMeta, fail
from src.platform.common.errors import (
    AuthenticationError,
    ConflictError,
    FeatureDisabledError,
    LicenseError,
    NotFoundError,
    PermissionDeniedError,
    PlatformError,
    PlatformValidationError,
    QuotaExceededError,
    SessionError,
    TenantIsolationError,
)

# Platform error code -> HTTP status.
STATUS_BY_CODE: dict[str, int] = {
    "validation_error": 422,
    "not_found": 404,
    "conflict": 409,
    "tenant_isolation_violation": 403,
    "authentication_failed": 401,
    "session_invalid": 401,
    "permission_denied": 403,
    "quota_exceeded": 429,
    "feature_disabled": 403,
    "license_error": 402,
    "configuration_error": 500,
    "platform_error": 500,
}

# Exception type -> code (fallback when the instance has no richer code).
_CODE_BY_TYPE = {
    PlatformValidationError: "validation_error",
    NotFoundError: "not_found",
    ConflictError: "conflict",
    TenantIsolationError: "tenant_isolation_violation",
    AuthenticationError: "authentication_failed",
    SessionError: "session_invalid",
    PermissionDeniedError: "permission_denied",
    QuotaExceededError: "quota_exceeded",
    FeatureDisabledError: "feature_disabled",
    LicenseError: "license_error",
}


def http_status_for(error: PlatformError) -> int:
    """Return the HTTP status code for a platform error."""
    return STATUS_BY_CODE.get(error.code, 500)


def to_response(error: PlatformError, *, meta: ResponseMeta | None = None) -> ApiResponse:
    """Translate a :class:`PlatformError` into an error :class:`ApiResponse`."""
    code = error.code or _CODE_BY_TYPE.get(type(error), "platform_error")
    return fail(code, error.message, meta=meta)
