"""Composition, architecture & end-to-end tests for the Integration Platform.

Verifies the integration composition root wires every module as lazy singletons,
that the whole ``src/platform/integrations`` tree is strictly **additive** (never
imports Phase 1-5 business logic), that it is reachable from the main platform
facade, and that an install→connect→sync→webhook→event flow works end-to-end
with tenant isolation preserved. Also covers the SDK foundation, observability
and the marketplace read-side.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.platform.bootstrap import build_platform
from src.platform.common.clock import FrozenClock
from src.platform.common.errors import TenantIsolationError
from src.platform.integrations import build_integration_platform
from src.platform.integrations.demo import build_integration_demo
from src.platform.integrations.gateway import ApiGateway
from src.platform.integrations.sdk import RestClientFoundation, SdkKind, sdk_catalog

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_DIR = ROOT / "src" / "platform" / "integrations"

_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from|import)\s+src\."
    r"(scoring|semantic|intelligence|hiring|recruiter|pipeline|reasoning|"
    r"ingestion|insights|comparison|talent_pool|interview|filtering|dashboard|"
    r"llm|ai|models)\b",
    re.MULTILINE,
)


# -- architecture: additive rule -------------------------------------------


def test_integrations_never_import_business_logic():
    offenders: list[str] = []
    for path in INTEGRATIONS_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"integrations imported business logic: {offenders}"


def test_every_integration_subpackage_imports():
    import importlib

    for name in [
        "common", "hris", "ats", "calendar", "communication", "documents",
        "gateway", "webhooks", "events", "sync", "observability", "sdk",
    ]:
        importlib.import_module(f"src.platform.integrations.{name}")


def test_app_exposes_integration_marketplace_nav():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Integration Marketplace" in app_src
    assert "_render_integration_marketplace_workspace" in app_src


# -- composition root -------------------------------------------------------


def test_build_integration_platform_wires_all_services():
    platform = build_integration_platform(clock=FrozenClock())
    for key in [
        "intg.registry", "intg.vault", "intg.observability", "intg.events",
        "intg.manager", "intg.webhooks", "intg.sync", "intg.gateway",
        "intg.marketplace",
    ]:
        assert platform.container.has(key)
    # Lazy singletons: same instance on repeated access.
    assert platform.manager is platform.manager
    assert isinstance(platform.gateway, ApiGateway)


def test_integration_platform_reachable_from_main_platform():
    main = build_platform(clock=FrozenClock())
    assert len(main.integrations.registry.keys()) == 40
    assert main.integrations is main.integrations  # lazy singleton


def test_two_integration_platforms_are_independent():
    a = build_integration_platform(clock=FrozenClock())
    b = build_integration_platform(clock=FrozenClock())
    a.manager.install("t1", "o1", "workday")
    assert len(a.manager.list("t1")) == 1
    assert len(b.manager.list("t1")) == 0


# -- end-to-end -------------------------------------------------------------


def test_install_connect_emits_event_and_records_telemetry():
    platform = build_integration_platform(clock=FrozenClock())
    integration = platform.manager.install("t1", "o1", "workday", credential="tok")
    platform.manager.connect("t1", integration.id)

    topics = [e.topic for e in platform.events.history(tenant_id="t1")]
    assert "integration.installed" in topics
    assert "integration.connected" in topics

    stats = platform.observability.stats_for("t1", integration.id)
    assert stats.connect_successes == 1
    logs = platform.observability.logs(tenant_id="t1")
    assert any(entry.event == "integration.connected" for entry in logs)


def test_demo_platform_is_seeded_and_isolated():
    platform = build_integration_demo()
    acme = platform.manager.list("org_acme")
    globex = platform.manager.list("org_globex")
    assert len(acme) == 4 and len(globex) == 3
    assert all(i.is_connected for i in acme + globex)
    # Cross-tenant read is refused at the repository boundary.
    with pytest.raises(TenantIsolationError):
        platform.manager.get("org_globex", acme[0].id)


def test_marketplace_overview_and_detail():
    platform = build_integration_demo()
    overview = platform.marketplace.overview("org_acme")
    assert overview.installed == 4
    assert overview.connected == 4
    assert overview.available_providers == 40

    integration = platform.manager.list("org_acme")[0]
    detail = platform.marketplace.detail("org_acme", integration.id)
    assert detail.definition.key == integration.definition_key
    assert detail.statistics is not None
    assert "records_processed" in detail.sync_health


def test_marketplace_search():
    platform = build_integration_demo()
    results = platform.marketplace.search("workday")
    assert any(d.key == "workday" for d in results)
    assert platform.marketplace.search("") == platform.marketplace.catalog()


# -- SDK foundation ---------------------------------------------------------


def test_sdk_catalog_covers_all_kinds():
    kinds = {s.kind for s in sdk_catalog()}
    assert kinds == set(SdkKind)


def test_rest_client_foundation_dispatches_through_gateway():
    from src.platform.integrations.gateway import (
        ApiPrincipal,
        ApiRoute,
        HttpMethod,
        Router,
        StaticApiKeyAuthHook,
    )

    auth = StaticApiKeyAuthHook()
    auth.register_key("k", ApiPrincipal(principal_id="u", tenant_id="t1", scopes=["*"]))
    router = Router()
    router.add(
        ApiRoute(method=HttpMethod.GET, path="/ping", name="ping", auth_required=False),
        handler=lambda ctx: {"pong": True},
    )
    gateway = ApiGateway(router=router, auth_hook=auth, clock=FrozenClock())
    client = RestClientFoundation(gateway=gateway, api_key="k")
    resp = client.get("/ping")
    assert resp.success and resp.data == {"pong": True}
