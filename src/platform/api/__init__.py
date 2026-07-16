"""Module 10 — API Foundation.

REST-ready contracts: standard response/error envelopes, error-code mapping,
offset and opaque-cursor pagination, declarative filtering/sorting, URL-prefix
versioning, an OpenAPI 3.1 skeleton, and a rate-limiter seam with a
deterministic token-bucket implementation. No existing endpoint is rewritten.
"""

from __future__ import annotations

from src.platform.api.errors import http_status_for, to_response
from src.platform.api.filtering import (
    FilterSpec,
    Operator,
    SortSpec,
    apply_filters,
    apply_sorts,
)
from src.platform.api.openapi import build_openapi
from src.platform.api.pagination import (
    CursorPage,
    Page,
    PageRequest,
    cursor_paginate,
    decode_cursor,
    encode_cursor,
    paginate,
)
from src.platform.api.ratelimit import (
    RateLimiter,
    RateLimitResult,
    TokenBucketRateLimiter,
)
from src.platform.api.responses import (
    ApiError,
    ApiResponse,
    ResponseMeta,
    fail,
    ok,
)
from src.platform.api.versioning import (
    CURRENT_VERSION,
    SUPPORTED_VERSIONS,
    ApiVersion,
    negotiate,
)

__all__ = [
    "ApiResponse",
    "ApiError",
    "ResponseMeta",
    "ok",
    "fail",
    "to_response",
    "http_status_for",
    "PageRequest",
    "Page",
    "paginate",
    "CursorPage",
    "cursor_paginate",
    "encode_cursor",
    "decode_cursor",
    "FilterSpec",
    "SortSpec",
    "Operator",
    "apply_filters",
    "apply_sorts",
    "ApiVersion",
    "CURRENT_VERSION",
    "SUPPORTED_VERSIONS",
    "negotiate",
    "build_openapi",
    "RateLimiter",
    "RateLimitResult",
    "TokenBucketRateLimiter",
]
