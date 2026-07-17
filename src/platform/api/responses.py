"""Standard API response envelopes (Module 10).

A single, consistent response shape for the future REST surface: a success
envelope with ``data`` + ``meta`` and an error envelope with a stable machine
code. Defining these as pydantic models keeps every endpoint's contract uniform
without rewriting any existing endpoint.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import Field

from src.platform.common.models import PlatformModel

T = TypeVar("T")


class ResponseMeta(PlatformModel):
    """Envelope metadata (request id, pagination, timing)."""

    request_id: str = ""
    api_version: str = "v1"
    pagination: dict[str, Any] = Field(default_factory=dict)


class ApiError(PlatformModel):
    """A structured, machine-readable error body."""

    code: str = "error"
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(PlatformModel, Generic[T]):
    """The uniform success/error envelope returned by every endpoint."""

    success: bool = True
    data: T | None = None
    error: ApiError | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


def ok(data: Any, *, meta: ResponseMeta | None = None) -> ApiResponse:
    """Build a success envelope around ``data``."""
    return ApiResponse(success=True, data=data, meta=meta or ResponseMeta())


def fail(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    meta: ResponseMeta | None = None,
) -> ApiResponse:
    """Build an error envelope."""
    return ApiResponse(
        success=False,
        error=ApiError(code=code, message=message, details=details or {}),
        meta=meta or ResponseMeta(),
    )
