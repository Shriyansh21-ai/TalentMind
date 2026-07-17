"""Tenant middleware (Module 2).

Framework-agnostic middleware that wraps a unit of work: it resolves the tenant
from an inbound request descriptor, binds the resulting context (so every
downstream call sees the right tenant), and guarantees the context is torn down
afterwards. Presented as a context manager so it composes with any host (a web
framework, a Streamlit page, a background job).
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Mapping
from typing import Any

from src.platform.tenancy.context import TenantContext, use_tenant
from src.platform.tenancy.resolver import TenantResolver


class TenantMiddleware:
    """Resolve-and-bind the tenant context around a unit of work."""

    def __init__(self, resolver: TenantResolver) -> None:
        self._resolver = resolver

    def resolve_request(self, request: Mapping[str, Any]) -> TenantContext:
        """Resolve a request descriptor into a :class:`TenantContext`.

        Recognised keys (checked in priority order): ``tenant_id``,
        ``organization_id``, ``slug``, ``host``. Optional: ``principal_id``,
        ``session_id``, ``request_id``.
        """
        return self._resolver.resolve(
            tenant_id=request.get("tenant_id"),
            organization_id=request.get("organization_id"),
            slug=request.get("slug"),
            host=request.get("host"),
            principal_id=request.get("principal_id"),
            session_id=request.get("session_id"),
            request_id=request.get("request_id"),
        )

    @contextlib.contextmanager
    def request(self, request: Mapping[str, Any]) -> Iterator[TenantContext]:
        """Enter the tenant context for ``request`` and reset it on exit."""
        context = self.resolve_request(request)
        with use_tenant(context):
            yield context
