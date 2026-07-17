"""The generic repository pattern used by every platform module.

A :class:`Repository` is a typed collection abstraction that separates domain
services from their storage mechanism (Clean Architecture / dependency
inversion). The only concrete implementation shipped here is
:class:`InMemoryRepository`; a future persistence layer (SQL, document store)
can implement the same protocol without touching a single service.

Tenant isolation is enforced *here*, at the boundary, rather than in each
service: any read/write that supplies a ``tenant_id`` will refuse to touch an
entity owned by a different tenant, raising :class:`TenantIsolationError`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Generic, Protocol, TypeVar

from src.platform.common.errors import (
    ConflictError,
    NotFoundError,
    TenantIsolationError,
)
from src.platform.common.models import Entity

E = TypeVar("E", bound=Entity)


class Repository(Protocol, Generic[E]):
    """Storage-agnostic collection of entities of type ``E``."""

    def add(self, entity: E) -> E: ...
    def get(self, entity_id: str, *, tenant_id: str | None = None) -> E | None: ...
    def require(self, entity_id: str, *, tenant_id: str | None = None) -> E: ...
    def list(
        self,
        *,
        tenant_id: str | None = None,
        where: Callable[[E], bool] | None = None,
    ) -> list[E]: ...
    def update(self, entity: E) -> E: ...
    def delete(self, entity_id: str, *, tenant_id: str | None = None) -> None: ...
    def count(self, *, tenant_id: str | None = None) -> int: ...


class InMemoryRepository(Generic[E]):
    """A dict-backed, tenant-isolating repository.

    Ordering is insertion order (Python dict guarantee) so listings are stable
    and deterministic — no wall-clock or hash ordering leaks into results.

    Args:
        name: Human label used in error messages ("organization", "session"…).
    """

    def __init__(self, name: str = "entity") -> None:
        self._name = name
        self._store: dict[str, E] = {}

    # -- isolation helper ---------------------------------------------------

    @staticmethod
    def _tenant_of(entity: E) -> str | None:
        """Return the entity's tenant id if it is tenant-scoped, else ``None``."""
        return getattr(entity, "tenant_id", None)

    def _assert_same_tenant(self, entity: E, tenant_id: str | None) -> None:
        """Raise if ``tenant_id`` is set and mismatches the entity's tenant."""
        if tenant_id is None:
            return
        owner = self._tenant_of(entity)
        if owner is not None and owner != tenant_id:
            raise TenantIsolationError(
                f"cross-tenant access to {self._name} '{entity.id}' denied "
                f"(owner={owner!r}, caller={tenant_id!r})"
            )

    # -- writes -------------------------------------------------------------

    def add(self, entity: E) -> E:
        """Insert a new entity. Raises :class:`ConflictError` on duplicate id."""
        if entity.id in self._store:
            raise ConflictError(f"{self._name} '{entity.id}' already exists")
        self._store[entity.id] = entity
        return entity

    def update(self, entity: E) -> E:
        """Replace an existing entity. Raises :class:`NotFoundError` if absent."""
        if entity.id not in self._store:
            raise NotFoundError(f"{self._name} '{entity.id}' not found")
        self._store[entity.id] = entity
        return entity

    def delete(self, entity_id: str, *, tenant_id: str | None = None) -> None:
        """Remove an entity (isolation-checked). No-op if it does not exist."""
        existing = self._store.get(entity_id)
        if existing is None:
            return
        self._assert_same_tenant(existing, tenant_id)
        del self._store[entity_id]

    # -- reads --------------------------------------------------------------

    def get(self, entity_id: str, *, tenant_id: str | None = None) -> E | None:
        """Return the entity, or ``None`` — raising if it belongs elsewhere."""
        entity = self._store.get(entity_id)
        if entity is None:
            return None
        self._assert_same_tenant(entity, tenant_id)
        return entity

    def require(self, entity_id: str, *, tenant_id: str | None = None) -> E:
        """Return the entity or raise :class:`NotFoundError`."""
        entity = self.get(entity_id, tenant_id=tenant_id)
        if entity is None:
            raise NotFoundError(f"{self._name} '{entity_id}' not found")
        return entity

    def list(
        self,
        *,
        tenant_id: str | None = None,
        where: Callable[[E], bool] | None = None,
    ) -> list[E]:
        """Return entities in insertion order, tenant-scoped and filtered.

        Args:
            tenant_id: If set, only entities owned by this tenant are returned
                (untenanted entities are excluded when a tenant filter is used).
            where: Optional predicate applied after tenant scoping.
        """
        results: list[E] = []
        for entity in self._store.values():
            if tenant_id is not None:
                owner = self._tenant_of(entity)
                if owner != tenant_id:
                    continue
            if where is not None and not where(entity):
                continue
            results.append(entity)
        return results

    def count(self, *, tenant_id: str | None = None) -> int:
        """Return the number of entities visible in ``tenant_id`` scope."""
        return len(self.list(tenant_id=tenant_id))

    def add_all(self, entities: Iterable[E]) -> list[E]:
        """Bulk-insert convenience wrapper around :meth:`add`."""
        return [self.add(e) for e in entities]

    def clear(self) -> None:
        """Drop all entities (used by tests and dev fixtures)."""
        self._store.clear()
