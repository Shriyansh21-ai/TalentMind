"""Shared foundation for the Enterprise Platform.

Base pydantic models, the platform exception hierarchy, id generation, a
pluggable clock and the generic repository pattern. Everything else in
:mod:`src.platform` builds on these primitives so the whole platform shares one
consistent, strongly-typed vocabulary with zero duplicated logic.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, FrozenClock, SystemClock, utcnow
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
from src.platform.common.ids import generate_id, slugify
from src.platform.common.models import (
    Entity,
    PlatformModel,
    TenantScopedEntity,
)
from src.platform.common.repository import InMemoryRepository, Repository

__all__ = [
    "Clock",
    "SystemClock",
    "FrozenClock",
    "utcnow",
    "PlatformError",
    "PlatformValidationError",
    "NotFoundError",
    "ConflictError",
    "TenantIsolationError",
    "PermissionDeniedError",
    "AuthenticationError",
    "SessionError",
    "QuotaExceededError",
    "FeatureDisabledError",
    "LicenseError",
    "generate_id",
    "slugify",
    "PlatformModel",
    "Entity",
    "TenantScopedEntity",
    "Repository",
    "InMemoryRepository",
]
