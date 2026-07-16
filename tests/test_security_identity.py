"""Module 1 tests — enterprise identity framework.

Registration, credential hashing (no plaintext stored), authentication with
uniform failure, lifecycle transitions, clock-driven session validity/expiry,
tenant isolation and future-provider placeholders.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.common.errors import TenantIsolationError
from src.platform.security.common.errors import IdentityError
from src.platform.security.identity import (
    IdentityManager,
    IdentityProviderType,
    IdentityStatus,
)
from src.platform.security.identity.providers import AzureAdProvider


def _manager() -> IdentityManager:
    return IdentityManager(clock=FrozenClock())


def test_register_and_authenticate():
    mgr = _manager()
    identity = mgr.register_identity("t1", "o1", "alice", secret="P@ssw0rd!!", roles=["r1"])
    assert identity.status == IdentityStatus.ACTIVE
    ctx, token = mgr.authenticate("t1", "alice", "P@ssw0rd!!")
    assert ctx.subject == "alice" and ctx.roles == ["r1"]
    assert len(token) == 64  # opaque plaintext returned once


def test_no_plaintext_secret_stored():
    mgr = _manager()
    mgr.register_identity("t1", "o1", "alice", secret="TopSecret123")
    # The credential store holds only (salt, hash) — never the plaintext.
    stored = mgr._credentials
    assert all("TopSecret123" not in "".join(v) for v in stored.values())


def test_wrong_and_unknown_credentials_uniformly_rejected():
    mgr = _manager()
    mgr.register_identity("t1", "o1", "alice", secret="P@ssw0rd!!")
    with pytest.raises(IdentityError):
        mgr.authenticate("t1", "alice", "wrong")
    with pytest.raises(IdentityError):
        mgr.authenticate("t1", "ghost", "whatever")


def test_suspended_identity_cannot_authenticate():
    mgr = _manager()
    identity = mgr.register_identity("t1", "o1", "alice", secret="P@ssw0rd!!")
    mgr.suspend("t1", identity.id)
    with pytest.raises(IdentityError):
        mgr.authenticate("t1", "alice", "P@ssw0rd!!")


def test_session_expiry_is_clock_driven():
    clock = FrozenClock()
    mgr = IdentityManager(token_ttl_seconds=3600, clock=clock)
    mgr.register_identity("t1", "o1", "alice", secret="P@ssw0rd!!")
    ctx, _ = mgr.authenticate("t1", "alice", "P@ssw0rd!!")
    assert mgr.validate_session("t1", ctx.session_id)
    clock.advance(seconds=3601)
    with pytest.raises(IdentityError):
        mgr.validate_session("t1", ctx.session_id)


def test_deactivate_revokes_sessions():
    mgr = _manager()
    identity = mgr.register_identity("t1", "o1", "alice", secret="P@ssw0rd!!")
    ctx, _ = mgr.authenticate("t1", "alice", "P@ssw0rd!!")
    mgr.deactivate("t1", identity.id)
    with pytest.raises(IdentityError):
        mgr.validate_session("t1", ctx.session_id)


def test_identities_are_tenant_isolated():
    mgr = _manager()
    identity = mgr.register_identity("t1", "o1", "alice", secret="x")
    with pytest.raises(TenantIsolationError):
        mgr.get("t2", identity.id)


def test_future_provider_is_registered_but_refuses():
    mgr = _manager()
    assert mgr.registry.has(IdentityProviderType.AZURE_AD)
    provider = AzureAdProvider()
    assert provider.describe()["status"] == "interface_only"
    with pytest.raises(IdentityError):
        provider.authenticate("t1", "alice", "secret")
