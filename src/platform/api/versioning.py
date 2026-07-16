"""API versioning (Module 10).

A minimal version-negotiation helper. The REST surface is versioned by URL
prefix (``/api/v1``); this resolves a requested version against the supported
set and identifies the current/default version.
"""

from __future__ import annotations

from enum import Enum


class ApiVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"


CURRENT_VERSION = ApiVersion.V1
SUPPORTED_VERSIONS = frozenset(v.value for v in ApiVersion)


def negotiate(requested: str | None) -> ApiVersion:
    """Resolve a requested version string to a supported :class:`ApiVersion`.

    Falls back to the current version when unspecified or unrecognised.
    """
    if not requested:
        return CURRENT_VERSION
    candidate = requested.strip().lower().lstrip("/")
    if candidate in SUPPORTED_VERSIONS:
        return ApiVersion(candidate)
    return CURRENT_VERSION
