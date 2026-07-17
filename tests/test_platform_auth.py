"""Tests for Module 3 — Authentication architecture."""

from __future__ import annotations

import faiss  # noqa: F401
import pytest

from src.platform.auth import AuthenticationManager, SessionStatus, UserStatus
from src.platform.auth.passwords import PasswordHasher, PasswordPolicy
from src.platform.common import (
    AuthenticationError,
    ConflictError,
    FrozenClock,
    PlatformValidationError,
    SessionError,
)

T = O = "org_1"
GOOD = "Sup3rSecret!!42"


def _mgr() -> AuthenticationManager:
    return AuthenticationManager(clock=FrozenClock())


# -- password policy + hashing ---------------------------------------------


def test_password_policy_violations():
    policy = PasswordPolicy()
    assert policy.violations("short")
    assert policy.violations(GOOD) == []
    with pytest.raises(PlatformValidationError):
        policy.validate("weak")


def test_password_hash_roundtrip_and_reject():
    hasher = PasswordHasher(iterations=1000)
    salt, digest, iters = hasher.hash(GOOD)
    assert hasher.verify(GOOD, salt=salt, expected=digest, iterations=iters)
    assert not hasher.verify("wrong", salt=salt, expected=digest, iterations=iters)


# -- registration + login ---------------------------------------------------


def test_register_normalises_email_and_stores_no_plaintext():
    mgr = _mgr()
    user = mgr.register_user(T, O, "Jane@Acme.com", GOOD)
    assert user.email == "jane@acme.com"
    assert user.status == UserStatus.ACTIVE
    cred = mgr.credentials.list(tenant_id=T)[0]
    assert GOOD not in (cred.hash + cred.salt)  # never stored raw


def test_duplicate_email_rejected():
    mgr = _mgr()
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    with pytest.raises(ConflictError):
        mgr.register_user(T, O, "jane@acme.com", GOOD)


def test_weak_password_rejected_on_register():
    with pytest.raises(PlatformValidationError):
        _mgr().register_user(T, O, "jane@acme.com", "weak")


def test_login_wrong_password_uniform_error():
    mgr = _mgr()
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    with pytest.raises(AuthenticationError):
        mgr.login(T, O, "jane@acme.com", "nope")
    with pytest.raises(AuthenticationError):  # unknown user, same error
        mgr.login(T, O, "ghost@acme.com", GOOD)


# -- sessions ---------------------------------------------------------------


def test_login_issues_validatable_session():
    mgr = _mgr()
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    issued = mgr.login(T, O, "jane@acme.com", GOOD)
    session = mgr.sessions.validate(T, issued.session_token)
    assert session.status == SessionStatus.ACTIVE


def test_refresh_rotates_and_blocks_replay():
    mgr = _mgr()
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    issued = mgr.login(T, O, "jane@acme.com", GOOD)
    rotated = mgr.sessions.refresh(T, issued.refresh_token)
    assert rotated.session_token != issued.session_token
    with pytest.raises(SessionError):
        mgr.sessions.refresh(T, issued.refresh_token)  # old token single-use


def test_session_expires_with_clock():
    clock = FrozenClock()
    mgr = AuthenticationManager(clock=clock)
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    issued = mgr.login(T, O, "jane@acme.com", GOOD)
    clock.advance(days=1)  # default TTL is 8h
    with pytest.raises(SessionError):
        mgr.sessions.validate(T, issued.session_token)


def test_logout_revokes_session():
    mgr = _mgr()
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    issued = mgr.login(T, O, "jane@acme.com", GOOD)
    mgr.logout(T, issued.session.id)
    with pytest.raises(SessionError):
        mgr.sessions.validate(T, issued.session_token)


def test_remember_me_extends_session():
    clock = FrozenClock()
    mgr = AuthenticationManager(clock=clock)
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    issued = mgr.login(T, O, "jane@acme.com", GOOD, remember_me=True)
    clock.advance(days=1)  # would expire a normal session
    assert mgr.sessions.validate(T, issued.session_token).remember_me


# -- verification + recovery ------------------------------------------------


def test_email_verification_flow():
    mgr = _mgr()
    user = mgr.register_user(T, O, "jane@acme.com", GOOD)
    token = mgr.email_verification.issue(user)
    mgr.email_verification.confirm(T, token)
    assert mgr.users.require(user.id, tenant_id=T).email_verified


def test_password_reset_blocks_reuse():
    mgr = _mgr()
    user = mgr.register_user(T, O, "bob@acme.com", GOOD)
    token = mgr.recovery.initiate(user)
    with pytest.raises(PlatformValidationError):
        mgr.reset_password(T, token, GOOD)  # same as current -> blocked
    token2 = mgr.recovery.initiate(user)
    mgr.reset_password(T, token2, "Different!!Pass99")


def test_users_are_tenant_isolated():
    mgr = _mgr()
    mgr.register_user(T, O, "jane@acme.com", GOOD)
    mgr.register_user("org_2", "org_2", "jane@acme.com", GOOD)  # same email, other tenant
    assert mgr.users.count(tenant_id=T) == 1
    assert mgr.users.count(tenant_id="org_2") == 1
