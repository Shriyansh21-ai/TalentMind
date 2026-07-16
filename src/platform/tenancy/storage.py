"""Tenant-scoped state storage (Module 2).

An in-memory, per-tenant key/value store used for lightweight tenant runtime
state. Every key is transparently namespaced by ``tenant_id`` via
:class:`~src.platform.tenancy.isolation.TenantIsolationGuard`, so one tenant can
never read or overwrite another tenant's keys — the store simply never exposes
an un-namespaced surface.

This is distinct from Module 11 (:mod:`src.platform.storage`), which abstracts
document/object/blob storage *providers*. This is tenant runtime state.
"""

from __future__ import annotations

from typing import Any

from src.platform.tenancy.isolation import TenantIsolationGuard


class TenantStorage:
    """A namespaced key/value store partitioned by tenant."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, tenant_id: str, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` within ``tenant_id``'s namespace."""
        self._data[TenantIsolationGuard.namespaced_key(tenant_id, key)] = value

    def get(self, tenant_id: str, key: str, default: Any = None) -> Any:
        """Return the tenant's value for ``key`` (or ``default``)."""
        return self._data.get(
            TenantIsolationGuard.namespaced_key(tenant_id, key), default
        )

    def delete(self, tenant_id: str, key: str) -> None:
        """Delete the tenant's ``key`` (no-op if absent)."""
        self._data.pop(TenantIsolationGuard.namespaced_key(tenant_id, key), None)

    def keys(self, tenant_id: str) -> list[str]:
        """Return the un-prefixed keys stored for ``tenant_id``."""
        prefix = TenantIsolationGuard.namespaced_key(tenant_id, "")
        return [k[len(prefix):] for k in self._data if k.startswith(prefix)]

    def purge(self, tenant_id: str) -> int:
        """Delete all of a tenant's keys; return how many were removed."""
        prefix = TenantIsolationGuard.namespaced_key(tenant_id, "")
        doomed = [k for k in self._data if k.startswith(prefix)]
        for k in doomed:
            del self._data[k]
        return len(doomed)
