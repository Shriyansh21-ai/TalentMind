"""Integration + architecture tests for the Enterprise Platform.

Verifies the composition root wires every module together, that the platform is
strictly **additive** (it never imports Phase 1-5 business logic), that every
sub-package imports cleanly, and that tenant isolation holds end-to-end.
"""

from __future__ import annotations

import faiss  # noqa: F401

import re
from pathlib import Path

import pytest

from src.platform.bootstrap import build_platform
from src.platform.common import FrozenClock, TenantIsolationError
from src.platform.rbac import AccessRequest, Action, Resource, Role, permission
from src.platform.subscription import Meter, PlanTier

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DIR = ROOT / "src" / "platform"

# Phase 1-5 business packages the platform must never depend on (additive rule).
_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from|import)\s+src\."
    r"(scoring|semantic|intelligence|hiring|recruiter|pipeline|reasoning|"
    r"ingestion|insights|comparison|talent_pool|interview|filtering|dashboard|"
    r"llm|ai|models)\b",
    re.MULTILINE,
)


# -- architecture: additive rule -------------------------------------------


def test_platform_never_imports_business_logic():
    """No file under src/platform may import a Phase 1-5 business package."""
    offenders: list[str] = []
    for path in PLATFORM_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"platform imported business logic: {offenders}"


def test_every_subpackage_imports():
    """All twelve module packages import without error."""
    import importlib

    for name in [
        "organizations", "tenancy", "auth", "rbac", "workspaces", "config",
        "subscription", "notifications", "audit", "api", "storage", "developer",
    ]:
        importlib.import_module(f"src.platform.{name}")


def test_app_exposes_platform_admin_nav():
    """The additive Platform Administration workspace is wired into app.py."""
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Platform Administration" in app_src
    assert "_render_platform_admin_workspace" in app_src


# -- integration: composition root -----------------------------------------


def test_build_platform_wires_all_services():
    platform = build_platform(clock=FrozenClock())
    for key in [
        "organizations", "tenants", "auth", "rbac", "workspaces", "config",
        "subscriptions", "notifications", "audit", "storage", "extensions",
    ]:
        assert platform.container.has(key)
    # Lazy singletons: same instance on repeated access.
    assert platform.organizations is platform.organizations


def test_provision_organization_end_to_end():
    platform = build_platform(clock=FrozenClock())
    org, tenant = platform.provision_organization(
        "Acme Inc", slug="acme", plan=PlanTier.PROFESSIONAL
    )
    assert tenant.id == org.id
    assert platform.subscriptions.remaining(org.id, Meter.SEATS) == 10
    assert platform.config.get(org.id) is not None
    assert platform.audit.verify_chain(org.id)
    assert platform.audit.query(org.id)[0].action == "organization.provisioned"


def test_end_to_end_identity_and_access():
    platform = build_platform(clock=FrozenClock())
    org, _ = platform.provision_organization("Acme", slug="acme")
    user = platform.auth.register_user(org.id, org.id, "admin@acme.com", "Sup3rSecret!!42")
    platform.access_control.assign(org.id, org.id, user.id, Role.ORGANIZATION_ADMIN)
    request = AccessRequest(
        tenant_id=org.id,
        principal_id=user.id,
        permission=permission(Resource.WORKSPACE, Action.CREATE),
    )
    assert platform.access_control.is_allowed(request)


def test_cross_tenant_isolation_end_to_end():
    platform = build_platform(clock=FrozenClock())
    acme, _ = platform.provision_organization("Acme", slug="acme")
    globex, _ = platform.provision_organization("Globex", slug="globex")

    acme_user = platform.auth.register_user(acme.id, acme.id, "a@acme.com", "Sup3rSecret!!42")
    # Globex must not see Acme's user — even a plain get is isolation-checked.
    with pytest.raises(TenantIsolationError):
        platform.auth.users.get(acme_user.id, tenant_id=globex.id)
    with pytest.raises(TenantIsolationError):
        platform.auth.users.require(acme_user.id, tenant_id=globex.id)
    # Acme still sees its own user, and Globex's user listing excludes it.
    assert platform.auth.users.require(acme_user.id, tenant_id=acme.id).id == acme_user.id
    assert acme_user.id not in {u.id for u in platform.auth.users.list(tenant_id=globex.id)}
    # ...and each tenant's audit chain is independent and intact.
    assert platform.audit.verify_chain(acme.id)
    assert platform.audit.verify_chain(globex.id)


def test_two_platforms_are_independent():
    a = build_platform(clock=FrozenClock())
    b = build_platform(clock=FrozenClock())
    a.provision_organization("Acme", slug="acme")
    assert len(a.organizations.list_organizations()) == 1
    assert len(b.organizations.list_organizations()) == 0
