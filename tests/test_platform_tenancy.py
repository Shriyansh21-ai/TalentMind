"""Tests for Module 2 — Multi-Tenancy (context, resolver, isolation, cache)."""

from __future__ import annotations

import faiss  # noqa: F401
import pytest

from src.platform.common import FrozenClock, TenantIsolationError
from src.platform.common.errors import NotFoundError
from src.platform.organizations import OrganizationService
from src.platform.tenancy import (
    TenantCache,
    TenantIsolationGuard,
    TenantService,
    TenantStatus,
    TenantStorage,
    current_context,
    require_context,
    use_tenant,
)


def _setup():
    clock = FrozenClock()
    orgs = OrganizationService(clock=clock)
    acme = orgs.create_organization("Acme", slug="acme")
    globex = orgs.create_organization("Globex", slug="globex")
    tenants = TenantService(orgs.repo, clock=clock)
    tenants.provision(acme)
    tenants.provision(globex)
    return orgs, tenants, acme, globex


def test_tenant_id_equals_organization_id():
    _orgs, tenants, acme, _globex = _setup()
    tenant = tenants.require(acme.id)
    assert tenant.id == acme.id == tenant.tenant_id
    assert tenant.is_active()


def test_provision_is_idempotent_guarded():
    from src.platform.common.errors import ConflictError

    orgs, tenants, acme, _ = _setup()
    with pytest.raises(ConflictError):
        tenants.provision(acme)


def test_resolver_by_organization_slug_and_domain():
    orgs, tenants, acme, _ = _setup()
    assert tenants.resolver.by_organization(acme.id).id == acme.id
    assert tenants.resolver.by_slug("acme").id == acme.id
    acme.branding.custom_domain = "careers.acme.com"
    orgs.repo.organizations.update(acme)
    assert tenants.resolver.by_domain("careers.acme.com").id == acme.id


def test_resolver_unknown_raises():
    _orgs, tenants, _acme, _ = _setup()
    with pytest.raises(NotFoundError):
        tenants.resolver.resolve(slug="does-not-exist")


def test_resolver_refuses_inactive_tenant():
    _orgs, tenants, acme, _ = _setup()
    tenants.set_status(acme.id, TenantStatus.SUSPENDED)
    with pytest.raises(TenantIsolationError):
        tenants.resolver.resolve(organization_id=acme.id)


def test_context_manager_binds_and_resets():
    _orgs, tenants, acme, _ = _setup()
    assert current_context() is None
    ctx = tenants.resolver.resolve(organization_id=acme.id)
    with use_tenant(ctx):
        assert current_context().tenant_id == acme.id
        assert require_context().organization_id == acme.id
    assert current_context() is None  # reset on exit


def test_isolation_guard_detects_foreign_entity():
    orgs, tenants, acme, globex = _setup()
    globex_unit = orgs.add_business_unit(globex.id, "Ops")
    ctx = tenants.resolver.resolve(organization_id=acme.id)
    with use_tenant(ctx):
        with pytest.raises(TenantIsolationError):
            TenantIsolationGuard.assert_entity_in_scope(globex_unit)


def test_tenant_storage_and_cache_are_namespaced():
    storage = TenantStorage()
    storage.set("t1", "k", "one")
    storage.set("t2", "k", "two")
    assert storage.get("t1", "k") == "one"
    assert storage.get("t2", "k") == "two"
    assert storage.keys("t1") == ["k"]

    cache = TenantCache()
    cache.set("t1", "cfg", 1)
    assert cache.get("t2", "cfg") is None  # never leaks across tenants
    assert cache.get("t1", "cfg") == 1
    cache.invalidate("t1")
    assert cache.get("t1", "cfg") is None


def test_middleware_enters_context_for_request():
    _orgs, tenants, acme, _ = _setup()
    with tenants.middleware.request({"organization_id": acme.id}) as ctx:
        assert ctx.tenant_id == acme.id
        assert current_context().tenant_id == acme.id
    assert current_context() is None
