"""Unit + tenant-isolation tests for the platform common foundation.

Covers the base models, id/clock helpers, the generic repository's tenant
isolation guarantees, and the lazy DI container (Phase 6 / Milestone 1).
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

import pytest

from src.platform.common import (
    Entity,
    FrozenClock,
    InMemoryRepository,
    TenantIsolationError,
    TenantScopedEntity,
    generate_id,
    slugify,
)
from src.platform.common.errors import ConflictError, NotFoundError
from src.platform.container import Container


class _Org(TenantScopedEntity):
    name: str


def _org(name: str = "Acme", tenant: str = "t1") -> _Org:
    return _Org(
        id=generate_id("org"), tenant_id=tenant, organization_id=tenant, name=name
    )


# -- ids / clock ------------------------------------------------------------


def test_generate_id_is_prefixed_and_unique():
    a, b = generate_id("org"), generate_id("org")
    assert a.startswith("org_") and a != b


def test_slugify_normalises():
    assert slugify("Acme, Inc.") == "acme-inc"
    assert slugify("") == "n-a"


def test_frozen_clock_advances_only_explicitly():
    clock = FrozenClock()
    start = clock.now()
    assert clock.now() == start
    later = clock.advance(days=1)
    assert later > start


# -- repository tenant isolation -------------------------------------------


def test_repository_add_get_require_roundtrip():
    repo: InMemoryRepository[_Org] = InMemoryRepository("org")
    org = repo.add(_org())
    assert repo.require(org.id).name == "Acme"
    assert repo.get("missing") is None
    with pytest.raises(NotFoundError):
        repo.require("missing")


def test_repository_rejects_duplicate_id():
    repo: InMemoryRepository[_Org] = InMemoryRepository("org")
    org = repo.add(_org())
    with pytest.raises(ConflictError):
        repo.add(org)


def test_repository_blocks_cross_tenant_get():
    repo: InMemoryRepository[_Org] = InMemoryRepository("org")
    org = repo.add(_org(tenant="t1"))
    with pytest.raises(TenantIsolationError):
        repo.get(org.id, tenant_id="t2")


def test_repository_list_is_tenant_scoped_and_ordered():
    repo: InMemoryRepository[_Org] = InMemoryRepository("org")
    a = repo.add(_org("A", "t1"))
    repo.add(_org("B", "t2"))
    c = repo.add(_org("C", "t1"))
    scoped = repo.list(tenant_id="t1")
    assert [o.id for o in scoped] == [a.id, c.id]  # insertion order preserved
    assert repo.count(tenant_id="t1") == 2
    assert repo.count(tenant_id="t2") == 1


def test_repository_delete_is_isolation_checked():
    repo: InMemoryRepository[_Org] = InMemoryRepository("org")
    org = repo.add(_org(tenant="t1"))
    with pytest.raises(TenantIsolationError):
        repo.delete(org.id, tenant_id="t2")
    repo.delete(org.id, tenant_id="t1")
    assert repo.get(org.id) is None


# -- DI container -----------------------------------------------------------


def test_container_lazy_singleton():
    built = []

    def factory(_c):
        built.append(1)
        return object()

    c = Container()
    c.register("svc", factory)
    assert not built  # lazy: nothing built until resolved
    first = c.resolve("svc")
    assert c.resolve("svc") is first  # memoised
    assert len(built) == 1


def test_container_non_singleton_builds_each_time():
    c = Container()
    c.register("svc", lambda _c: object(), singleton=False)
    assert c.resolve("svc") is not c.resolve("svc")


def test_container_resolves_dependencies_via_container():
    c = Container()
    c.register("dep", lambda _c: 21)
    c.register("svc", lambda cc: cc.resolve("dep") * 2)
    assert c.resolve("svc") == 42


def test_container_unknown_key_raises():
    from src.platform.common.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        Container().resolve("nope")


def test_entity_touch_updates_timestamp():
    clock = FrozenClock()
    entity = Entity(id="x", created_at=clock.now(), updated_at=clock.now())
    original = entity.updated_at
    clock.advance(seconds=5)
    entity.touch(clock.now())
    assert entity.updated_at > original
