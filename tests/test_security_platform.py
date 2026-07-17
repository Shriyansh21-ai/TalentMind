"""Composition, architecture & end-to-end tests for the Security Platform.

Verifies the security composition root wires every module as lazy singletons,
that the whole ``src/platform/security`` tree is strictly **additive** (never
imports Phase 1-5 business logic), that it is reachable from the main platform
facade, and that an identity→authz→audit→analytics flow works end-to-end.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.platform.bootstrap import build_platform
from src.platform.common.clock import FrozenClock
from src.platform.security import build_security_platform
from src.platform.security.audit.models import AuditEventType
from src.platform.security.authorization import AuthorizationRequest
from src.platform.security.demo import build_security_demo

ROOT = Path(__file__).resolve().parents[1]
SECURITY_DIR = ROOT / "src" / "platform" / "security"

_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from|import)\s+src\."
    r"(scoring|semantic|intelligence|hiring|recruiter|pipeline|reasoning|"
    r"ingestion|insights|comparison|talent_pool|interview|filtering|dashboard|"
    r"llm|ai|models)\b",
    re.MULTILINE,
)


# -- architecture -----------------------------------------------------------


def test_security_never_imports_business_logic():
    offenders: list[str] = []
    for path in SECURITY_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"security imported business logic: {offenders}"


def test_every_security_subpackage_imports():
    import importlib

    for name in [
        "common",
        "identity",
        "authorization",
        "audit",
        "secrets",
        "observability",
        "monitoring",
        "governance",
        "compliance",
        "threat",
        "configuration",
        "incidents",
        "analytics",
    ]:
        importlib.import_module(f"src.platform.security.{name}")


def test_app_exposes_security_operations_nav():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Security & Operations Center" in app_src
    assert "_render_security_operations_workspace" in app_src


# -- composition root -------------------------------------------------------


def test_build_security_platform_wires_all_services():
    sp = build_security_platform(clock=FrozenClock())
    for key in [
        "sec.identity",
        "sec.authorization",
        "sec.audit",
        "sec.secrets",
        "sec.observability",
        "sec.monitoring",
        "sec.governance",
        "sec.compliance",
        "sec.threat",
        "sec.configuration",
        "sec.incidents",
        "sec.analytics",
    ]:
        assert sp.container.has(key)
    assert sp.identity is sp.identity  # lazy singleton


def test_security_reachable_from_main_platform():
    main = build_platform(clock=FrozenClock())
    assert main.security is main.security
    assert main.security.compliance.standards()  # service usable


def test_two_security_platforms_are_independent():
    a = build_security_platform(clock=FrozenClock())
    b = build_security_platform(clock=FrozenClock())
    a.identity.register_identity("t1", "o1", "alice", secret="x")
    assert len(a.identity.list("t1")) == 1
    assert len(b.identity.list("t1")) == 0


# -- end-to-end -------------------------------------------------------------


def test_end_to_end_identity_authz_audit_analytics():
    sp = build_security_platform(clock=FrozenClock())
    sp.identity.register_identity("t1", "o1", "alice", secret="P@ss12345", roles=["recruiter"])
    ctx, _ = sp.identity.authenticate("t1", "alice", "P@ss12345")

    sp.authorization.hierarchy.define_group("t1", "o1", "rec", ["candidate:read"])
    sp.authorization.hierarchy.define_role("t1", "o1", "recruiter", groups=["rec"])
    allowed = sp.authorization.is_allowed(
        AuthorizationRequest(
            tenant_id="t1", subject=ctx.subject, roles=ctx.roles, permission="candidate:read"
        )
    )
    assert allowed

    sp.audit.record("t1", "o1", AuditEventType.AUTHENTICATION, "login", actor_id="alice")
    sp.audit.record("t1", "o1", AuditEventType.AUTHORIZATION, "candidate.read", actor_id="alice")
    assert sp.audit.verify_chain("t1")

    dashboard = sp.analytics.executive_dashboard("t1", "o1")
    assert set(dashboard) == {"security", "audit", "policy", "incidents", "monitoring"}
    assert dashboard["audit"]["total"] == 2


def test_demo_platform_is_seeded():
    sp = build_security_demo()
    assert len(sp.identity.list("org_acme")) == 2
    assert sp.audit.count("org_acme") >= 5
    assert sp.threat.threat_report("org_acme", "org_acme").total_events >= 2
    assert sp.incidents.report("org_acme")["total"] >= 2
