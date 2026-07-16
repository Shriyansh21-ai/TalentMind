"""Module 4 tests — enterprise secrets framework.

No-plaintext storage, reveal at point of use, redaction, rotation, clock-driven
expiration, access tracking, revocation and cloud provider placeholders.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.security.common.errors import SecretError
from src.platform.security.secrets import (
    AzureKeyVaultProvider,
    SecretManager,
    SecretStatus,
    cloud_provider_interfaces,
)


def _manager() -> SecretManager:
    return SecretManager(clock=FrozenClock())


def test_store_reveal_and_no_plaintext_in_provider():
    mgr = _manager()
    meta = mgr.store("t1", "o1", "api_key", "super-secret-1234")
    assert mgr.reveal("t1", meta.ref) == "super-secret-1234"
    # The underlying provider store never contains the plaintext verbatim.
    raw = "".join(mgr.provider._store.values())  # type: ignore[attr-defined]
    assert "super-secret-1234" not in raw


def test_redaction_hides_value():
    mgr = _manager()
    meta = mgr.store("t1", "o1", "api_key", "super-secret-1234")
    assert mgr.redacted("t1", meta.ref).endswith("1234")
    assert "super-secret" not in mgr.redacted("t1", meta.ref)


def test_access_tracking():
    mgr = _manager()
    meta = mgr.store("t1", "o1", "api_key", "secret-value")
    mgr.reveal("t1", meta.ref, accessor="alice")
    mgr.reveal("t1", meta.ref, accessor="bob")
    assert meta.access_count == 2
    assert len(mgr.access_log("t1")) == 2


def test_rotation_updates_version_and_value():
    mgr = _manager()
    meta = mgr.store("t1", "o1", "api_key", "old-value")
    mgr.rotate("t1", meta.ref, "new-value")
    assert meta.version == 2
    assert mgr.reveal("t1", meta.ref) == "new-value"


def test_rotation_due_after_interval():
    clock = FrozenClock()
    mgr = SecretManager(clock=clock)
    mgr.store("t1", "o1", "api_key", "value", rotation_interval_days=30)
    assert mgr.rotation_due("t1") == []
    clock.advance(days=31)
    assert len(mgr.rotation_due("t1")) == 1


def test_expiration_blocks_reveal():
    clock = FrozenClock()
    mgr = SecretManager(clock=clock)
    meta = mgr.store("t1", "o1", "api_key", "value", ttl_seconds=60)
    clock.advance(seconds=61)
    assert meta.status_at(clock.now()) == SecretStatus.EXPIRED
    with pytest.raises(SecretError):
        mgr.reveal("t1", meta.ref)


def test_revoke_deletes_value():
    mgr = _manager()
    meta = mgr.store("t1", "o1", "api_key", "value")
    mgr.revoke("t1", meta.ref)
    with pytest.raises(SecretError):
        mgr.reveal("t1", meta.ref)


def test_cross_tenant_access_denied():
    mgr = _manager()
    meta = mgr.store("t1", "o1", "api_key", "value")
    with pytest.raises(SecretError):
        mgr.reveal("t2", meta.ref)


def test_cloud_providers_are_placeholders():
    assert len(cloud_provider_interfaces()) == 4
    provider = AzureKeyVaultProvider()
    assert provider.describe()["status"] == "interface_only"
    with pytest.raises(SecretError):
        provider.read("t1", "ref")
