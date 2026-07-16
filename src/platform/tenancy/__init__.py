"""Module 2 — Multi-Tenancy.

A true multi-tenant architecture built around a single isolation key
(``tenant_id`` == organization id). Provides the tenant model, an ambient
:class:`TenantContext` (contextvar-backed for concurrency), a resolver and
middleware for entering tenant scope at the edge, an isolation guard, and
namespaced per-tenant cache and storage — everything needed for safe horizontal
scaling with no cross-tenant data leakage.
"""

from __future__ import annotations

from src.platform.tenancy.cache import TenantCache
from src.platform.tenancy.context import (
    TenantContext,
    current_context,
    require_context,
    use_tenant,
)
from src.platform.tenancy.isolation import TenantIsolationGuard
from src.platform.tenancy.middleware import TenantMiddleware
from src.platform.tenancy.models import (
    IsolationMode,
    Tenant,
    TenantConfiguration,
    TenantFeatures,
    TenantLimits,
    TenantStatus,
)
from src.platform.tenancy.resolver import TenantResolver
from src.platform.tenancy.service import TenantService
from src.platform.tenancy.storage import TenantStorage

__all__ = [
    "Tenant",
    "TenantStatus",
    "IsolationMode",
    "TenantConfiguration",
    "TenantFeatures",
    "TenantLimits",
    "TenantContext",
    "current_context",
    "require_context",
    "use_tenant",
    "TenantIsolationGuard",
    "TenantResolver",
    "TenantMiddleware",
    "TenantCache",
    "TenantStorage",
    "TenantService",
]
