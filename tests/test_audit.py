"""Tests for the Enterprise Hiring Audit & Explainability Platform (Phase 5 / M4).

Covers the audit pipeline end-to-end — the score-free schema, the deterministic
composer, decision-trace / provenance / evidence-graph / reasoning / timeline /
responsibility / governance-explanation / readiness / history modules, the archive
provider interface (default-unavailable + injected path), the engine assembly
(reusing the whole chain), safety/no-fabrication guarantees, automatic
registration and copilot delegation — all offline with synthetic candidates.
"""

from __future__ import annotations

import json

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.agents.audit import approvals as approvals_mod
from src.ai.agents.audit import decision_trace as trace_mod
from src.ai.agents.audit import evidence_graph as graph_mod
from src.ai.agents.audit import governance as governance_mod
from src.ai.agents.audit import history as history_mod
from src.ai.agents.audit import provenance as provenance_mod
from src.ai.agents.audit import validators
from src.ai.agents.audit.agent import (
    AuditInput,
    build_audit_evidence,
)
from src.ai.agents.audit.audit_engine import (
    HiringAuditEngine,
    NullAuditArchiveProvider,
)
from src.ai.agents.audit.composer import compose_audit_narrative
from src.ai.agents.audit.schemas import AuditNarrative, HiringAuditReport
from src.ai.agents.audit.templates import AGENT_CATALOG
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard

JD = "Senior Machine Learning Engineer. Python, PyTorch, AWS, Kubernetes, LLMs. 8+ years. Lead and mentor."

_FULL_SOURCES = [e.source for e in AGENT_CATALOG]


class _ComplianceProvider:
    """Injected governance provider (verifies approvals + documents)."""

    def is_available(self) -> bool:
        return True

    def get_approvals(self, candidate_id):
        return {
            role: {"approved": True, "by": "Approver"}
            for role in ["Recruiter", "Hiring Manager", "HR", "Finance", "Legal", "Executive"]
        }

    def get_documents(self, candidate_id):
        return {"executive_report": True, "interview_packet": True}

    def get_audit_events(self, candidate_id):
        return [{"event": "committee"}, {"event": "offer"}]


class _ArchiveProvider:
    """Injected audit-archive provider (returns stored history)."""

    def is_available(self) -> bool:
        return True

    def get_history(self, candidate_id):
        return [{"decision": "prior offer", "outcome": "hired"}]


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _report(compliance_provider=None, archive_provider=None, **kw) -> HiringAuditReport:
    engine = HiringAuditEngine(
        ai_runner=_runner(),
        compliance_provider=compliance_provider,
        archive_provider=archive_provider,
    )
    return engine.build(
        candidate=make_candidate(candidate_id=kw.pop("candidate_id", "CAND_1")),
        jd=kw.pop("jd", JD),
        generated_on="2026-07-16",
        **kw,
    )


def _ctx(sources=None, data_available=False, **over):
    base = {
        "candidate_id": "CAND_1",
        "evidence_sources": sources if sources is not None else list(_FULL_SOURCES),
        "workflow": {"status": "Requires Review", "completed": 6, "total": 8},
        "approvals": {
            "approvals": [
                {
                    "approver": "Recruiter",
                    "required": True,
                    "state": "Requires Review",
                    "reason": "r",
                },
                {
                    "approver": "Hiring Manager",
                    "required": True,
                    "state": "Requires Review",
                    "reason": "r",
                },
                {"approver": "HR", "required": True, "state": "Requires Review", "reason": "r"},
                {"approver": "Finance", "required": False, "state": "Not Required", "reason": "r"},
                {"approver": "Legal", "required": False, "state": "Not Required", "reason": "r"},
                {
                    "approver": "Executive",
                    "required": False,
                    "state": "Not Required",
                    "reason": "r",
                },
            ],
            "required": ["Recruiter", "Hiring Manager", "HR"],
            "outstanding": ["Recruiter", "Hiring Manager", "HR"],
        },
        "documentation": {"missing": [], "present": ["Resume"]},
        "audit": {
            "findings": [{"dimension": "Evidence chain", "status": "Complete"}],
            "status": "Needs Investigation",
        },
        "governance_risk": {"level": "Medium", "drivers": ["Outstanding approvals"]},
        "exceptions": [],
        "review": {"rationale": "Recommend Compliance review."},
        "equity_risk_level": "Unknown",
        "data_available": data_available,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Registration + schema
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("hiring_audit")


def test_composer_registered():
    assert has_composer(AuditNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("hiring_audit")
    assert any(a.descriptor.name == "hiring_audit" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(AuditNarrative)


def test_tool_registered_in_builtin():
    import src.ai.tools.builtin  # noqa: F401
    from src.ai.tools.registry import registry as tool_registry

    assert tool_registry.has("hiring_audit")


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def test_composer_never_empty_and_validates():
    out = compose_audit_narrative({})
    assert out["executive_summary"].strip()
    AuditNarrative(**out)


def test_composer_states_no_archive():
    out = compose_audit_narrative(
        {
            "data_available": False,
            "history": {"status_message": "No historical audit archive connected."},
        }
    )
    assert "archive" in out["data_availability_note"].lower()


def test_build_evidence_packs_all_sections():
    ev = build_audit_evidence(AuditInput(candidate_id="C1"))
    for key in (
        "decision_trace",
        "provenance",
        "reasoning",
        "timeline",
        "responsibility",
        "governance_explanations",
        "audit_readiness",
        "history",
        "agents_participated",
    ):
        assert key in ev


# ---------------------------------------------------------------------------
# Module 1 — Decision trace
# ---------------------------------------------------------------------------


def test_decision_trace_observed_when_sources_present():
    trace = trace_mod.build_decision_trace(_ctx())
    statuses = {s.stage: s.status for s in trace}
    assert statuses["Committee decision"] == "Observed"
    assert statuses["Final Decision"] == "Observed"
    assert len(trace) == len(AGENT_CATALOG) + 1


def test_decision_trace_unavailable_when_sources_absent():
    trace = trace_mod.build_decision_trace(_ctx(sources=["Resume Analyst Agent"]))
    statuses = {s.stage: s.status for s in trace}
    assert statuses["Resume analysis"] == "Observed"
    assert statuses["Committee decision"] == "Unavailable"
    assert statuses["Final Decision"] == "Unavailable"  # no committee -> no final decision


# ---------------------------------------------------------------------------
# Module 2 — Provenance + evidence graph
# ---------------------------------------------------------------------------


def test_provenance_present_and_absent():
    records = provenance_mod.build_provenance(
        _ctx(sources=["Resume Analyst Agent", "AI Hiring Committee"])
    )
    by_source = {r.evidence_source: r for r in records}
    assert by_source["Resume Analyst Agent"].register == "Observed"
    assert by_source["Pay Equity Guardian"].register == "Unavailable"
    assert by_source["Pay Equity Guardian"].confidence == "Unknown"


def test_evidence_graph_edges_active_only_between_present_nodes():
    graph = graph_mod.build_evidence_graph(_ctx())
    present = {n.id for n in graph.nodes if n.present}
    for e in graph.edges:
        if e.active:
            assert e.source in present and e.target in present


def test_evidence_graph_final_node_present_with_committee():
    graph = graph_mod.build_evidence_graph(_ctx())
    final = [n for n in graph.nodes if n.kind == "decision"][0]
    assert final.present is True


# ---------------------------------------------------------------------------
# Module 5 — Human vs AI responsibility (never blurred)
# ---------------------------------------------------------------------------


def test_responsibility_separates_ai_and_human():
    matrix = approvals_mod.build_responsibility_matrix(_ctx())
    ai = [d for d in matrix if d.responsible_party == "AI"]
    human = [d for d in matrix if d.responsible_party != "AI"]
    assert ai and human
    # Committee is an AI vote.
    assert any(d.kind == "Committee vote" and d.responsible_party == "AI" for d in matrix)
    # Human approvals are unverified without a connected system.
    assert all(d.status == "Unverified" for d in human)


def test_responsibility_human_observed_with_provider():
    ctx = _ctx()
    for a in ctx["approvals"]["approvals"]:
        if a["required"]:
            a["state"] = "Complete"
    matrix = approvals_mod.build_responsibility_matrix(ctx)
    human = [d for d in matrix if d.responsible_party != "AI"]
    assert all(d.status == "Observed" for d in human)


# ---------------------------------------------------------------------------
# Module 7 — Audit readiness
# ---------------------------------------------------------------------------


def test_audit_readiness_flags_missing():
    readiness = governance_mod.build_audit_readiness(_ctx(sources=["Resume Analyst Agent"]))
    assert readiness.missing_evidence  # most agents absent
    assert readiness.missing_approvals == ["Recruiter", "Hiring Manager", "HR"]
    assert readiness.readiness_level in ("Low", "Medium")


# ---------------------------------------------------------------------------
# Module 8 — Historical reconstruction
# ---------------------------------------------------------------------------


def test_history_unavailable_by_default():
    h = history_mod.reconstruct_history("CAND_1", NullAuditArchiveProvider())
    assert h.available is False
    assert "no historical" in h.status_message.lower()


def test_history_available_with_provider():
    h = history_mod.reconstruct_history("CAND_1", _ArchiveProvider())
    assert h.available is True
    assert len(h.records) == 1


# ---------------------------------------------------------------------------
# Engine — reuses the chain, reconstructs the journey
# ---------------------------------------------------------------------------


def test_engine_produces_report_without_archive():
    report = _report()
    assert isinstance(report, HiringAuditReport)
    assert report.data_available is False
    # The whole chain participated (11 agents).
    assert len(report.agents_participated) == len(AGENT_CATALOG)
    assert all(s.status == "Observed" for s in report.decision_trace)
    # Human approvals unverified without an archive.
    human = [d for d in report.responsibility if d.responsible_party != "AI"]
    assert all(d.status in ("Unverified", "Unavailable") for d in human)
    assert report.history.available is False
    assert report.narrative.executive_summary


def test_engine_reconstructs_full_chain_evidence():
    report = _report()
    for label in (
        "AI Hiring Committee",
        "Compensation Governance Agent",
        "Pay Equity Guardian",
        "Hiring Compliance",
        "Resume Risk Detection",
    ):
        assert label in report.evidence_sources


def test_engine_with_providers_verifies_humans_and_history():
    report = _report(
        compliance_provider=_ComplianceProvider(),
        archive_provider=_ArchiveProvider(),
        candidate_id="CAND_2",
    )
    assert report.data_available is True
    human_observed = [
        d for d in report.responsibility if d.responsible_party != "AI" and d.status == "Observed"
    ]
    assert human_observed
    assert report.history.available is True


def test_engine_is_deterministic():
    r1 = _report(candidate_id="CAND_DET")
    r2 = _report(candidate_id="CAND_DET")
    assert [s.stage for s in r1.decision_trace] == [s.stage for s in r2.decision_trace]
    assert r1.audit_readiness.readiness_level == r2.audit_readiness.readiness_level


def test_report_to_dict_is_serializable():
    assert json.dumps(_report().to_dict())
    assert json.dumps(
        _report(
            compliance_provider=_ComplianceProvider(),
            archive_provider=_ArchiveProvider(),
            candidate_id="CAND_J",
        ).to_dict()
    )


def test_charts_present():
    report = _report()
    for key in (
        "decision_flow",
        "evidence_graph",
        "timeline",
        "approval_chain",
        "agent_participation",
        "governance_health",
        "audit_readiness",
    ):
        assert key in report.charts


# ---------------------------------------------------------------------------
# Safety (Module 14)
# ---------------------------------------------------------------------------


def test_no_fabrication_no_legal_opinion():
    report = _report()
    warnings = validators.validate_safety(
        report.narrative, report.responsibility, report.history, report.data_available
    )
    # The only expected warnings are coverage warnings, not safety violations.
    assert all("flagged" not in w for w in warnings)


def test_human_never_observed_without_archive():
    report = _report()
    for d in report.responsibility:
        if d.responsible_party != "AI":
            assert d.status != "Observed"


# ---------------------------------------------------------------------------
# Copilot integration (Module 11)
# ---------------------------------------------------------------------------


def test_copilot_routes_audit_questions():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Why was this candidate hired?",
        "Explain this hiring decision.",
        "Show decision timeline.",
        "Show evidence.",
        "Generate audit report.",
        "Show approval history.",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.HIRING_AUDIT


def test_copilot_audit_intent_selects_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.HIRING_AUDIT) == ["hiring_audit"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Is this hiring process compliant?": Intent.HIRING_COMPLIANCE,
        "Show audit trail": Intent.HIRING_COMPLIANCE,
        "What approvals are missing?": Intent.HIRING_COMPLIANCE,
        "Why are we offering this compensation?": Intent.COMPENSATION_GOVERNANCE,
        "Is this offer fair?": Intent.PAY_EQUITY,
        "Who should approve this?": Intent.PAY_EQUITY,
        "Why is this candidate ranked so high?": Intent.EXPLAIN_RANKING,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
        "Generate executive report": Intent.EXECUTIVE_REPORT,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_audit_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Why was this candidate hired? CAND_0000001", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.HIRING_AUDIT
    assert "hiring_audit" in [t["name"] for t in turn.tools_used]
    assert "Hiring Audit" in turn.evidence_sources
    assert turn.answer
