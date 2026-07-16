"""Module 1 tests — integration framework, registry, manager and secrets.

Exercises the core of the Enterprise Integration Platform: provider discovery
and the registry, the integration lifecycle (install → connect → configure →
disconnect → uninstall), credential storage as opaque references, and
tenant-isolation of installed integrations.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.common.errors import TenantIsolationError
from src.platform.integrations.common import (
    CredentialVault,
    InMemorySecretProvider,
    IntegrationStatus,
    ProviderCategory,
    ProviderNotFoundError,
    build_default_registry,
)
from src.platform.integrations.common.errors import (
    CredentialError,
    ProviderConfigurationError,
)
from src.platform.integrations.manager import IntegrationManager


def _manager() -> IntegrationManager:
    clock = FrozenClock()
    return IntegrationManager(registry=build_default_registry(), clock=clock)


# -- registry & discovery ---------------------------------------------------


def test_registry_discovers_all_provider_families():
    registry = build_default_registry()
    counts = registry.categories()
    assert counts[ProviderCategory.HRIS] == 12
    assert counts[ProviderCategory.ATS] == 10
    assert counts[ProviderCategory.CALENDAR] == 4
    assert counts[ProviderCategory.COMMUNICATION] == 7
    assert counts[ProviderCategory.DOCUMENT] == 7
    assert len(registry.keys()) == 40


def test_registry_definitions_are_cached_and_sorted():
    registry = build_default_registry()
    first = registry.definition("workday")
    second = registry.definition("workday")
    assert first is second  # cached
    hris = registry.definitions(category=ProviderCategory.HRIS)
    names = [d.metadata.display_name for d in hris]
    assert names == sorted(names, key=str.lower)


def test_registry_unknown_provider_raises():
    registry = build_default_registry()
    with pytest.raises(ProviderNotFoundError):
        registry.get("does_not_exist")


# -- lifecycle --------------------------------------------------------------


def test_install_connect_configure_lifecycle():
    manager = _manager()
    integration = manager.install(
        "t1", "o1", "greenhouse", credential="gh-key", sync_enabled=True
    )
    assert integration.status == IntegrationStatus.NOT_CONNECTED
    assert integration.category == ProviderCategory.ATS

    connected = manager.connect("t1", integration.id)
    assert connected.is_connected
    assert connected.status == IntegrationStatus.CONNECTED
    assert connected.health.is_healthy

    configured = manager.configure("t1", integration.id, settings={"region": "us"})
    assert configured.configuration.settings["region"] == "us"

    disconnected = manager.disconnect("t1", integration.id)
    assert disconnected.status == IntegrationStatus.NOT_CONNECTED


def test_install_validates_unsupported_capability():
    manager = _manager()
    # Email provider does not support sync — enabling it must fail validation.
    with pytest.raises(ProviderConfigurationError):
        manager.install("t1", "o1", "email", sync_enabled=True)


def test_uninstall_revokes_credential():
    manager = _manager()
    integration = manager.install("t1", "o1", "slack", credential="xoxb-123")
    ref = integration.configuration.credential_ref
    assert manager.vault.resolve("t1", ref) == "xoxb-123"
    manager.uninstall("t1", integration.id)
    with pytest.raises(CredentialError):
        manager.vault.resolve("t1", ref)


def test_require_connected_raises_when_not_connected():
    manager = _manager()
    integration = manager.install("t1", "o1", "workday")
    from src.platform.integrations.common.errors import IntegrationNotConnectedError

    with pytest.raises(IntegrationNotConnectedError):
        manager.require_connected("t1", integration.id)


# -- tenant isolation -------------------------------------------------------


def test_installed_integrations_are_tenant_isolated():
    manager = _manager()
    a = manager.install("tenant_a", "tenant_a", "workday")
    manager.install("tenant_b", "tenant_b", "lever")

    assert {i.id for i in manager.list("tenant_a")} == {a.id}
    # Tenant B cannot read Tenant A's integration — even a plain get is checked.
    with pytest.raises(TenantIsolationError):
        manager.get("tenant_b", a.id)


# -- secrets / vault --------------------------------------------------------


def test_vault_stores_no_plaintext_and_redacts():
    provider = InMemorySecretProvider()
    vault = CredentialVault(provider, clock=FrozenClock())
    ref = vault.issue("t1", "super-secret-value")
    # The raw store never contains the plaintext.
    assert "super-secret-value" not in "".join(provider._store.values())
    assert vault.resolve("t1", ref.ref) == "super-secret-value"
    assert vault.redacted("t1", ref.ref).endswith("alue")


def test_vault_cross_tenant_access_denied():
    vault = CredentialVault(clock=FrozenClock())
    ref = vault.issue("t1", "secret")
    with pytest.raises(CredentialError):
        vault.resolve("t2", ref.ref)


def test_vault_expiry_is_clock_driven():
    clock = FrozenClock()
    vault = CredentialVault(clock=clock)
    ref = vault.issue("t1", "secret", ttl_seconds=60)
    assert vault.resolve("t1", ref.ref) == "secret"
    clock.advance(seconds=120)
    with pytest.raises(CredentialError):
        vault.resolve("t1", ref.ref)
