"""Tenant context (Module 2).

The :class:`TenantContext` is the ambient "who am I acting for" carried through a
unit of work. It is stored in a :class:`contextvars.ContextVar` so it is safe
under concurrency (threads / async tasks each see their own current tenant) —
essential for horizontal scaling where one process serves many tenants.

Always enter a context via :func:`use_tenant` (a context manager) rather than
setting the var directly, so it is guaranteed to be reset on exit.
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import Iterator

from pydantic import Field

from src.platform.common.errors import TenantIsolationError
from src.platform.common.models import PlatformModel


class TenantContext(PlatformModel):
    """The active tenant (and optionally principal) for a unit of work.

    Attributes:
        tenant_id: Active tenant isolation key (== organization id).
        organization_id: Active organization id.
        principal_id: Authenticated user id, if any.
        session_id: Active session id, if any.
        request_id: Correlation id for tracing/audit.
    """

    tenant_id: str
    organization_id: str
    principal_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


_CURRENT: ContextVar[TenantContext | None] = ContextVar(
    "talentmind_tenant_context", default=None
)


def current_context() -> TenantContext | None:
    """Return the active :class:`TenantContext`, or ``None`` if unset."""
    return _CURRENT.get()


def require_context() -> TenantContext:
    """Return the active context or raise :class:`TenantIsolationError`.

    Used by code paths that must never run outside a resolved tenant.
    """
    ctx = _CURRENT.get()
    if ctx is None:
        raise TenantIsolationError("no active tenant context")
    return ctx


@contextlib.contextmanager
def use_tenant(context: TenantContext) -> Iterator[TenantContext]:
    """Bind ``context`` as the active tenant for the duration of the block.

    Restores the previous context (including ``None``) on exit, even on error.
    """
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)
