"""Tests for the Enterprise Hiring Compliance Intelligence System (Phase 5 / M3).

Covers the compliance pipeline end-to-end — the score-free schema, the
deterministic composer, workflow / approval / policy / documentation / audit /
exception / risk / review modules, the governance-data provider interface
(default-unavailable + injected path), the engine assembly (reusing the whole
intelligence chain), scenario simulation, safety/no-legal-advice guarantees,
automatic registration and copilot delegation — all offline with synthetic
candidates.
"""

from __future__ import annotations

import json

import faiss  # noqa: F401  (faiss-before-torch load order)

from conftest import make_candidate

from src.ai.config.settings import AISettings
from src.ai.core.runner import AgentRunner
from src.ai.core.registry import registry
from src.ai.validators.safety import SafetyGuard
from src.ai.providers.composers import has_composer

from src.ai.agents.compliance.agent import (
    ComplianceInput,
    build_compliance_evidence,
    compliance_agent,
)
from src.ai.agents.compliance.compliance_report import (
    HiringComplianceEngine,
    NullComplianceDataProvider,
)
from src.ai.agents.compliance.composer import compose_compliance_narrative
from src.ai.agents.compliance.schemas import (
    ApprovalMatrix,
    ComplianceNarrative,
    HiringComplianceReport,
)
from src.ai.agents.compliance import approval_engine as approval_mod
from src.ai.agents.compliance import documentation as documentation_mod
from src.ai.agents.compliance import policy_engine as policy_mod
from src.ai.agents.compliance import workflow as workflow_mod
from src.ai.agents.compliance import validators
from src.ai.agents.compliance.templates import get_policy, list_policies

from src.ai.orchestration.registry.agent_registry import orchestration_registry

JD = "Senior Machine Learning Engineer. Python, PyTorch, AWS, Kubernetes, LLMs. 8+ years. Lead and mentor."


class _FullProvider:
    """An injected governance provider: all approvals + documents present."""

    def is_available(self) -> bool:
        return True

    def get_approvals(self, candidate_id):
        return {role: {"approved": True, "by": "Approver"} for role in
                ["Recruiter", "Hiring Manager", "HR", "Finance", "Legal", "Executive"]}

    def get_documents(self, candidate_id):
        return {"executive_report": True, "interview_packet": True}

    def get_audit_events(self, candidate_id):
        return [{"event": "committee"}, {"event": "offer"}, {"event": "approval"}]


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _report(provider=None, **kw) -> HiringComplianceReport:
    engine = HiringComplianceEngine(ai_runner=_runner(), data_provider=provider)
    return engine.build(
        candidate=make_candidate(candidate_id=kw.pop("candidate_id", "CAND_1")),
        jd=kw.pop("jd", JD),
        generated_on="2026-07-15",
        **kw,
    )


def _ctx(**over):
    base = {
        "candidate_id": "CAND_1",
        "evidence_sources": [
            "Resume Analyst Agent", "JD Analyst Agent", "Interview Intelligence",
            "AI Hiring Committee", "Compensation Governance Agent", "Pay Equity Guardian",
        ],
        "required_approvers": ["Recruiter", "Hiring Manager", "HR"],
        "approval_reasons": {},
        "hire_type": "Growth Hire",
        "comp_target": 50.0,
        "executive_hire": False,
        "critical_hire": False,
        "salary_above_threshold": False,
        "remote_hire": False,
        "equity_risk_level": "Unknown",
        "pay_policy_alignment": "Not Evaluable",
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Registration + schema
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("hiring_compliance")


def test_composer_registered():
    assert has_composer(ComplianceNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("hiring_compliance")
    assert any(a.descriptor.name == "hiring_compliance" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(ComplianceNarrative)


def test_tool_registered_in_builtin():
    from src.ai.tools.registry import registry as tool_registry
    import src.ai.tools.builtin  # noqa: F401

    assert tool_registry.has("hiring_compliance")


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def test_composer_never_empty_and_validates():
    out = compose_compliance_narrative({})
    assert out["executive_summary"].strip()
    ComplianceNarrative(**out)


def test_composer_states_not_legal_advice():
    out = compose_compliance_narrative({})
    assert "not legal advice" in out["executive_summary"].lower()


def test_build_evidence_packs_all_sections():
    ev = build_compliance_evidence(ComplianceInput(candidate_id="C1"))
    for key in ("workflow", "approvals", "policy_checks", "documentation", "audit",
                "governance_risk", "exceptions", "review", "data_available"):
        assert key in ev


# ---------------------------------------------------------------------------
# Module 4 — Documentation
# ---------------------------------------------------------------------------


def test_documentation_present_from_evidence():
    review = documentation_mod.validate_documentation(_ctx(), NullComplianceDataProvider())
    present = review.present()
    assert "Resume" in present
    assert "Committee Decision" in present
    # Executive report / interview packet are generatable but not confirmed filed.
    states = {d.name: d.state for d in review.documents}
    assert states["Executive Report"] == "Requires Review"


def test_documentation_missing_when_evidence_absent():
    review = documentation_mod.validate_documentation(
        _ctx(evidence_sources=["Resume Analyst Agent"]), NullComplianceDataProvider()
    )
    assert "Committee Decision" in review.missing()


def test_documentation_confirmed_by_provider():
    review = documentation_mod.validate_documentation(_ctx(), _FullProvider())
    states = {d.name: d.state for d in review.documents}
    assert states["Executive Report"] == "Present"


# ---------------------------------------------------------------------------
# Module 2 — Approvals
# ---------------------------------------------------------------------------


def test_approvals_required_from_context():
    matrix = approval_mod.build_approval_matrix(_ctx(), NullComplianceDataProvider())
    assert matrix.required() == ["Recruiter", "Hiring Manager", "HR"]
    # Without a provider, required approvals are pending review (not assumed complete).
    assert matrix.outstanding() == ["Recruiter", "Hiring Manager", "HR"]
    for a in matrix.approvals:
        if a.required:
            assert a.state == "Requires Review"


def test_approvals_complete_with_provider():
    matrix = approval_mod.build_approval_matrix(_ctx(), _FullProvider())
    assert matrix.outstanding() == []
    for a in matrix.approvals:
        if a.required:
            assert a.state == "Complete"


# ---------------------------------------------------------------------------
# Module 1 — Workflow
# ---------------------------------------------------------------------------


def test_workflow_steps_completed_from_evidence():
    matrix = approval_mod.build_approval_matrix(_ctx(), NullComplianceDataProvider())
    docs = documentation_mod.validate_documentation(_ctx(), NullComplianceDataProvider())
    wf = workflow_mod.assess_workflow(_ctx(), matrix, docs)
    statuses = {s.name: s.status for s in wf.steps}
    assert statuses["Committee decision"] == "Completed"
    assert statuses["Required approvals complete"] == "Requires Review"
    assert wf.status in ("Compliant", "Incomplete", "Requires Review")


def test_workflow_incomplete_when_critical_step_missing():
    ctx = _ctx(evidence_sources=["Resume Analyst Agent"])  # no interview/committee
    matrix = approval_mod.build_approval_matrix(ctx, NullComplianceDataProvider())
    docs = documentation_mod.validate_documentation(ctx, NullComplianceDataProvider())
    wf = workflow_mod.assess_workflow(ctx, matrix, docs)
    assert wf.status == "Incomplete"


def test_workflow_compliant_with_full_provider():
    matrix = approval_mod.build_approval_matrix(_ctx(), _FullProvider())
    docs = documentation_mod.validate_documentation(_ctx(), _FullProvider())
    wf = workflow_mod.assess_workflow(_ctx(), matrix, docs)
    assert wf.status == "Compliant"
    assert wf.completed == wf.total


# ---------------------------------------------------------------------------
# Module 3 — Policy (configurable)
# ---------------------------------------------------------------------------


def test_policy_not_applicable_for_standard_hire():
    matrix = approval_mod.build_approval_matrix(_ctx(), NullComplianceDataProvider())
    checks = policy_mod.evaluate_policies(list_policies(), _ctx(), matrix)
    # Growth hire, no threshold, not remote -> all policies Not Applicable.
    assert all(c.status == "Not Applicable" for c in checks)


def test_policy_committee_satisfied_for_executive_hire():
    ctx = _ctx(executive_hire=True, critical_hire=True, hire_type="Critical Hire",
               salary_above_threshold=True)
    matrix = approval_mod.build_approval_matrix(ctx, _FullProvider())
    checks = {c.policy_key: c for c in policy_mod.evaluate_policies(list_policies(), ctx, matrix)}
    # Committee is in evidence -> exec-hire-committee compliant.
    assert checks["exec_hire_committee"].status == "Compliant"
    # Finance approval complete via provider -> salary-threshold compliant.
    assert checks["salary_threshold_finance"].status == "Compliant"


def test_policy_violation_when_committee_absent_for_executive_hire():
    ctx = _ctx(executive_hire=True, evidence_sources=["Resume Analyst Agent"])
    matrix = approval_mod.build_approval_matrix(ctx, NullComplianceDataProvider())
    checks = {c.policy_key: c for c in policy_mod.evaluate_policies(list_policies(), ctx, matrix)}
    assert checks["exec_hire_committee"].status == "Violation"


def test_policies_are_configurable_data():
    assert get_policy("exec_hire_committee").requires == "committee_complete"
    assert len(list_policies()) >= 4


# ---------------------------------------------------------------------------
# Engine — reuses the chain, assembles the report
# ---------------------------------------------------------------------------


def test_engine_produces_report_without_governance_data():
    report = _report()
    assert isinstance(report, HiringComplianceReport)
    assert report.data_available is False
    # Core intelligence steps completed; approvals/documentation pending review.
    statuses = {s.name: s.status for s in report.workflow.steps}
    assert statuses["Committee decision"] == "Completed"
    assert statuses["Pay-equity review"] == "Completed"
    assert report.approvals.outstanding()  # cannot confirm approvals without a system
    assert report.audit.status == "Needs Investigation"
    assert report.narrative.executive_summary
    assert "Pay Equity Guardian" in report.evidence_sources


def test_engine_produces_compliant_report_with_provider():
    report = _report(provider=_FullProvider(), candidate_id="CAND_2")
    assert report.data_available is True
    assert report.workflow.status == "Compliant"
    assert report.approvals.outstanding() == []
    assert report.governance_risk.level == "Low"


def test_engine_is_deterministic():
    r1 = _report(candidate_id="CAND_DET")
    r2 = _report(candidate_id="CAND_DET")
    assert r1.workflow.status == r2.workflow.status
    assert r1.governance_risk.level == r2.governance_risk.level


def test_engine_scenarios_present():
    report = _report()
    names = [s.name for s in report.scenarios]
    assert "Hiring without committee" in names
    assert "Hiring without interview" in names
    assert len(report.scenarios) == 5


def test_report_to_dict_is_serializable():
    assert json.dumps(_report().to_dict())
    assert json.dumps(_report(provider=_FullProvider(), candidate_id="CAND_J").to_dict())


def test_charts_present():
    report = _report()
    for key in ("compliance_status", "workflow_completion", "approval_flow",
                "executive_approval_matrix", "audit_readiness", "governance_health", "missing_documentation"):
        assert key in report.charts


# ---------------------------------------------------------------------------
# Safety (Module 14)
# ---------------------------------------------------------------------------


def test_no_legal_advice_language():
    report = _report(provider=_FullProvider(), candidate_id="CAND_S")
    warnings = validators.validate_safety(report.narrative, report.approvals, report.data_available)
    assert warnings == []


def test_approvals_never_complete_without_system():
    report = _report(candidate_id="CAND_NS")
    for a in report.approvals.approvals:
        if a.required:
            assert a.state != "Complete"


# ---------------------------------------------------------------------------
# Copilot integration (Module 11)
# ---------------------------------------------------------------------------


def test_copilot_routes_compliance_questions():
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState
    from src.ai.copilot.models import Intent

    clf = IntentClassifier()
    for message in [
        "Is this hiring process compliant?",
        "Generate compliance report",
        "What approvals are missing?",
        "Show audit trail",
        "Is executive approval required?",
        "What documentation is missing?",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.HIRING_COMPLIANCE


def test_copilot_compliance_intent_selects_tool():
    from src.ai.copilot.tool_selector import select_tools
    from src.ai.copilot.models import Intent

    assert select_tools(Intent.HIRING_COMPLIANCE) == ["hiring_compliance"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState
    from src.ai.copilot.models import Intent

    clf = IntentClassifier()
    cases = {
        "Why are we offering this compensation?": Intent.COMPENSATION_GOVERNANCE,
        "What is the negotiation strategy?": Intent.COMPENSATION_GOVERNANCE,
        "Is this offer fair?": Intent.PAY_EQUITY,
        "Who should approve this?": Intent.PAY_EQUITY,
        "Does this violate pay policy?": Intent.PAY_EQUITY,
        "Generate interview": Intent.INTERVIEW_STUDIO,
        "Create an interview plan": Intent.GENERATE_INTERVIEW_PLAN,
        "Generate executive report": Intent.EXECUTIVE_REPORT,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_compliance_end_to_end():
    from src.ai.tools.provider import InMemoryCandidateRepository
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Is this hiring process compliant for CAND_0000001?", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.HIRING_COMPLIANCE
    assert "hiring_compliance" in [t["name"] for t in turn.tools_used]
    assert "Hiring Compliance" in turn.evidence_sources
    assert turn.answer
