"""Permission tests for Module 4 — Role-Based Access Control."""

from __future__ import annotations

import faiss  # noqa: F401
import pytest

from src.platform.common import FrozenClock, PermissionDeniedError
from src.platform.common.errors import PlatformValidationError
from src.platform.rbac import (
    AccessControlService,
    AccessRequest,
    Action,
    Resource,
    Role,
    ScopeType,
    matches,
    permission,
)

T = O = "org_1"


def _acl() -> AccessControlService:
    return AccessControlService(clock=FrozenClock())


def _req(principal: str, res: Resource, act: Action, **scope) -> AccessRequest:
    return AccessRequest(
        tenant_id=T, principal_id=principal, permission=permission(res, act), **scope
    )


# -- permission matching ----------------------------------------------------


def test_permission_wildcards_match():
    assert matches("workspace:*", "workspace:read")
    assert matches("*:*", "anything:delete")
    assert not matches("workspace:read", "candidate:read")


# -- role grants ------------------------------------------------------------


def test_recruiter_can_read_candidates_not_delete_users():
    acl = _acl()
    acl.assign(T, O, "u", Role.RECRUITER)
    assert acl.is_allowed(_req("u", Resource.CANDIDATE, Action.READ))
    assert not acl.is_allowed(_req("u", Resource.USER, Action.DELETE))


def test_platform_admin_wildcard_allows_everything():
    acl = _acl()
    acl.assign(T, O, "root", Role.PLATFORM_ADMIN, scope_type=ScopeType.PLATFORM)
    assert acl.is_allowed(
        AccessRequest(tenant_id=T, principal_id="root", permission="billing:delete")
    )


def test_platform_only_role_rejected_below_platform_scope():
    acl = _acl()
    with pytest.raises(PlatformValidationError):
        acl.assign(T, O, "x", Role.PLATFORM_ADMIN)  # default org scope


def test_workspace_scoped_grant_limited_to_that_workspace():
    acl = _acl()
    acl.assign(T, O, "iv", Role.INTERVIEWER, scope_type=ScopeType.WORKSPACE, scope_id="ws_1")
    assert acl.is_allowed(_req("iv", Resource.CANDIDATE, Action.READ, workspace_id="ws_1"))
    assert not acl.is_allowed(_req("iv", Resource.CANDIDATE, Action.READ, workspace_id="ws_2"))


def test_authorize_raises_permission_denied():
    acl = _acl()
    acl.assign(T, O, "viewer", Role.VIEWER)
    with pytest.raises(PermissionDeniedError):
        acl.authorize(_req("viewer", Resource.USER, Action.DELETE))


def test_default_deny_for_unknown_principal():
    acl = _acl()
    assert not acl.is_allowed(_req("nobody", Resource.DASHBOARD, Action.READ))


def test_grants_are_tenant_isolated():
    acl = _acl()
    acl.assign(T, O, "u", Role.RECRUITER)
    acl.assign("org_2", "org_2", "u", Role.HR_DIRECTOR)
    assert len(acl.assignments_for(T, "u")) == 1
    assert len(acl.assignments_for("org_2", "u")) == 1


def test_unknown_role_rejected():
    acl = _acl()
    with pytest.raises(PlatformValidationError):
        acl.assign(T, O, "u", "wizard")


def test_custom_role_definition():
    acl = _acl()
    acl.define_custom_role("kiosk", [permission(Resource.DASHBOARD, Action.READ)])
    acl.assign(T, O, "k", "kiosk")
    assert acl.is_allowed(_req("k", Resource.DASHBOARD, Action.READ))
    assert not acl.is_allowed(_req("k", Resource.REPORT, Action.READ))


def test_all_twelve_roles_defined():
    acl = _acl()
    for role in Role:
        assert role.value in acl.definitions
