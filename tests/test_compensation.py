"""Tests for the Enterprise Compensation Governance System (Phase 5 / Milestone 1).

Covers the governance pipeline end-to-end — the score-free schema, the
deterministic composer, the pay-band model, offer scenarios, market position,
budget, negotiation, internal-equity readiness (HRIS-ready, no connectors), the
governance checks, the flagship transparency audit trail, safety/no-fabrication,
automatic registration (AI platform + composer + orchestration) and copilot
delegation — all offline with synthetic candidates (no dataset/provider/LLM).
"""

from __future__ import annotations

import json

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.agents.compensation import market_position as market_mod
from src.ai.agents.compensation import negotiation as negotiation_mod
from src.ai.agents.compensation import salary_strategy as strategy_mod
from src.ai.agents.compensation import validators
from src.ai.agents.compensation.agent import (
    CompensationInput,
    build_compensation_evidence,
)
from src.ai.agents.compensation.composer import compose_compensation_narrative
from src.ai.agents.compensation.governance import (
    CompensationGovernanceEngine,
    build_governance_checks,
)
from src.ai.agents.compensation.internal_equity import (
    NullCompensationDataProvider,
    assess_internal_equity,
)
from src.ai.agents.compensation.pay_band import derive_pay_band
from src.ai.agents.compensation.schemas import (
    CompensationNarrative,
    CompensationRange,
    CompensationReport,
)
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard

JD = """Senior Machine Learning Engineer
- Design and own scalable ML systems in production
- Lead and mentor engineers
Requirements: 8+ years, Python, PyTorch, AWS, Kubernetes, LLMs
"""


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _report(jd: str = JD, **kw) -> CompensationReport:
    engine = CompensationGovernanceEngine(ai_runner=_runner(), **kw.pop("engine_kw", {}))
    return engine.build(
        candidate=make_candidate(candidate_id=kw.pop("candidate_id", "CAND_1")),
        jd=jd,
        generated_on="2026-07-15",
        **kw,
    )


# ---------------------------------------------------------------------------
# Registration + schema (final requirements, Modules 14/16)
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("compensation_governance")


def test_composer_registered():
    assert has_composer(CompensationNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("compensation_governance")
    assert any(a.descriptor.name == "compensation_governance" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(CompensationNarrative)


def test_narrative_top_level_has_no_score_fields():
    for name in CompensationNarrative.field_names():
        assert not any(
            tok in name.lower() for tok in ("score", "rating", "percent", "confidence_value")
        )


def test_tool_registered_in_builtin():
    import src.ai.tools.builtin  # noqa: F401
    from src.ai.tools.registry import registry as tool_registry

    assert tool_registry.has("compensation_governance")


# ---------------------------------------------------------------------------
# Composer (offline reasoning) — restates, never fabricates
# ---------------------------------------------------------------------------


def test_composer_never_empty_summary_and_validates():
    out = compose_compensation_narrative({})
    assert out["executive_summary"].strip()
    CompensationNarrative(**out)


def test_composer_states_internal_heuristic_model():
    out = compose_compensation_narrative(
        {
            "recommended_range": {
                "currency": "INR",
                "minimum": 40,
                "target": 50,
                "maximum": 60,
                "unit": "LPA",
            }
        }
    )
    assert "internal heuristic model" in out["market_position_note"].lower()


def test_composer_reports_equity_unavailable():
    out = compose_compensation_narrative({})
    assert "unavailable" in out["internal_equity_note"].lower()


def test_build_evidence_packs_all_sources():
    payload = CompensationInput(candidate_id="C1", intelligence={"technical_score": 80})
    evidence = build_compensation_evidence(payload)
    for key in (
        "candidate_comp",
        "resume",
        "jd",
        "committee",
        "intelligence",
        "timeline",
        "risk",
        "recommendation",
        "interview",
        "recommended_range",
    ):
        assert key in evidence


# ---------------------------------------------------------------------------
# Module 1 — Compensation recommendation (a defensible RANGE, never a point)
# ---------------------------------------------------------------------------


def test_pay_band_is_a_range_not_a_point():
    evidence = {
        "candidate_comp": {
            "currency": "INR",
            "unit": "LPA",
            "expected_min": 40,
            "expected_max": 60,
        },
        "candidate_overview": {"years_of_experience": 9},
        "intelligence": {"technical_score": 90, "leadership_score": 75, "confidence": 80},
    }
    band = derive_pay_band(evidence)
    assert band.minimum < band.target < band.maximum
    assert band.currency == "INR" and band.unit == "LPA"
    assert any("internal heuristic" in a.lower() for a in band.assumptions)


def test_pay_band_uses_candidate_expectation_as_observed_evidence():
    evidence = {"candidate_comp": {"expected_min": 40, "expected_max": 60}}
    band = derive_pay_band(evidence)
    assert any("Observed Evidence" in b for b in band.basis)


def test_pay_band_falls_back_to_assumption_without_expectation():
    evidence = {"candidate_overview": {"years_of_experience": 6}}
    band = derive_pay_band(evidence)
    assert band.minimum < band.maximum
    assert any("Assumption" in a for a in band.assumptions)


def test_pay_band_applies_premiums():
    strong = derive_pay_band(
        {
            "candidate_comp": {"expected_min": 40, "expected_max": 60},
            "intelligence": {"technical_score": 95, "leadership_score": 90},
            "committee": {"consensus": {"recommendation": "Strong Hire"}},
        }
    )
    plain = derive_pay_band({"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    assert strong.target > plain.target  # premiums lifted the target


# ---------------------------------------------------------------------------
# Module 5 — Offer scenarios
# ---------------------------------------------------------------------------


def test_scenarios_are_ordered_and_named():
    band = derive_pay_band({"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    scenarios = strategy_mod.build_scenarios({}, band)
    names = [s.name for s in scenarios]
    assert names == ["Conservative Offer", "Competitive Offer", "Premium Offer", "Aggressive Offer"]
    targets = [s.comp_range.target for s in scenarios]
    assert targets == sorted(targets)  # conservative < ... < aggressive
    for s in scenarios:
        assert s.advantages and s.risks


# ---------------------------------------------------------------------------
# Module 4 — Market position (never fabricates market data)
# ---------------------------------------------------------------------------


def test_market_position_declares_no_external_data():
    band = derive_pay_band({"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    mp = market_mod.assess_market_position(
        {"candidate_comp": {"expected_min": 40, "expected_max": 60}}, band
    )
    assert mp.data_available is False
    assert "internal heuristic model" in mp.data_note.lower()
    assert mp.position in (
        "Below Market",
        "Market Competitive",
        "Premium",
        "Strategic Premium",
        "Budget-Constrained",
    )


# ---------------------------------------------------------------------------
# Module 6 — Negotiation intelligence (separates observed evidence from advice)
# ---------------------------------------------------------------------------


def test_negotiation_separates_observed_evidence():
    band = derive_pay_band({"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    ng = negotiation_mod.build_negotiation(
        {
            "candidate_comp": {
                "expected_min": 40,
                "expected_max": 60,
                "offer_acceptance_rate": 0.8,
                "notice_period_days": 30,
            }
        },
        band,
    )
    assert ng.observed_evidence
    assert ng.strategy and ng.fallback_strategy
    assert ng.acceptance_likelihood in ("High", "Moderate", "Low")


# ---------------------------------------------------------------------------
# Module 8 — Internal equity readiness (HRIS-ready; no payroll connectors)
# ---------------------------------------------------------------------------


def test_internal_equity_unavailable_by_default():
    band = derive_pay_band({"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    eq = assess_internal_equity({}, band, NullCompensationDataProvider())
    assert eq.available is False
    assert eq.status_message == "Internal equity validation unavailable."
    assert eq.hris_interfaces_ready  # future integration points prepared


def test_internal_equity_evaluates_with_injected_provider():
    class StubProvider:
        def is_available(self) -> bool:
            return True

        def get_pay_band(self, role, level):
            return {"min": 40.0, "max": 55.0}

        def get_peer_compensation(self, role, level):
            return [{"compensation": 52.0}]

    band = CompensationRange(minimum=45, target=50, maximum=58)
    eq = assess_internal_equity(
        {"candidate_overview": {"title": "ML Engineer", "years_of_experience": 9}},
        band,
        StubProvider(),
    )
    assert eq.available is True
    dims = {c.dimension for c in eq.checks}
    assert "Pay-band consistency" in dims
    assert "Compression risk" in dims


# ---------------------------------------------------------------------------
# Module 3 — Governance checks (every conclusion explains WHY)
# ---------------------------------------------------------------------------


def test_governance_checks_explain_why():
    evidence = {
        "candidate_overview": {"years_of_experience": 9},
        "intelligence": {"technical_score": 90, "leadership_score": 80},
    }
    band = derive_pay_band(evidence | {"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    checks = build_governance_checks(evidence, band, "Critical Hire")
    dims = {c.dimension for c in checks}
    for expected in (
        "Internal policy alignment",
        "Offer consistency",
        "Experience alignment",
        "Skill premium",
        "Leadership premium",
        "Strategic hiring premium",
        "Replacement vs. Growth hire",
    ):
        assert expected in dims
    for c in checks:
        assert c.rationale  # every conclusion explains why


# ---------------------------------------------------------------------------
# Engine — consumes existing intelligence, assembles a unified report
# ---------------------------------------------------------------------------


def test_engine_produces_unified_report():
    report = _report()
    assert isinstance(report, CompensationReport)
    assert report.narrative.executive_summary
    assert report.recommended_range.minimum < report.recommended_range.maximum
    assert report.justification
    assert report.governance_checks
    assert report.scenarios
    assert report.audit_trail.decision_id


def test_engine_consumes_many_sources():
    report = _report()
    assert len(report.evidence_sources) >= 6
    assert "Candidate stated expectation" in report.evidence_sources


def test_engine_is_deterministic():
    r1 = _report(candidate_id="CAND_DET")
    r2 = _report(candidate_id="CAND_DET")
    assert r1.recommended_range.target == r2.recommended_range.target
    assert r1.market_position.position == r2.market_position.position


def test_engine_without_committee():
    engine = CompensationGovernanceEngine(ai_runner=_runner())
    report = engine.build(
        candidate=make_candidate(), jd=JD, run_committee=False, generated_on="2026-07-15"
    )
    assert report.recommended_range.minimum < report.recommended_range.maximum
    assert report.narrative.executive_summary


def test_report_to_dict_is_serializable():
    assert json.dumps(_report().to_dict())


def test_no_regression_warnings_for_full_evidence():
    report = _report()
    # No fabrication warnings should fire for a well-formed report.
    fab = [w for w in report.warnings if "fabricat" in w.lower() or "collapsed" in w.lower()]
    assert fab == []


# ---------------------------------------------------------------------------
# Module 12 — Transparency audit trail (the flagship)
# ---------------------------------------------------------------------------


def test_audit_trail_complete():
    report = _report()
    audit = report.audit_trail
    assert audit.decision_id.startswith("COMP-")
    assert audit.decision_timestamp == "2026-07-15"
    assert audit.evidence_sources
    assert "Compensation Governance Agent" in audit.agents_consulted
    assert audit.reasoning_chain
    assert audit.approvals_required  # Finance + HR at minimum
    assert "Finance" in audit.approvals_required and "HR" in audit.approvals_required
    assert audit.human_review_status == "Pending Human Review"


def test_audit_trail_exportable():
    report = _report()
    text = report.audit_trail.to_export_text()
    assert "COMPENSATION DECISION AUDIT TRAIL" in text
    assert report.audit_trail.decision_id in text
    assert "Reasoning Chain:" in text


def test_critical_hire_requires_executive_sponsor():
    # A strong-hire committee stance should classify a critical hire needing exec sign-off.
    from src.ai.agents.compensation import budget as budget_mod
    from src.ai.agents.compensation import offer_justification as oj

    evidence = {"committee": {"consensus": {"recommendation": "Strong Hire"}}}
    band = derive_pay_band(evidence | {"candidate_comp": {"expected_min": 40, "expected_max": 60}})
    budget = budget_mod.assess_budget(evidence, band)
    assert budget.hire_type == "Critical Hire"
    audit = oj.build_audit_trail(
        evidence,
        band,
        market_mod.assess_market_position(evidence, band),
        budget,
        decision_id="COMP-X",
        decision_timestamp="2026-07-15",
        equity_available=False,
    )
    assert "Executive Sponsor" in audit.approvals_required


# ---------------------------------------------------------------------------
# Safety (Module 16)
# ---------------------------------------------------------------------------


def test_validate_no_fabrication_passes_for_clean_report():
    report = _report()
    warnings = validators.validate_no_fabrication(
        report.recommended_range, report.market_position, report.internal_equity
    )
    assert warnings == []


def test_available_sources_lists_candidate_expectation():
    report = _report()
    assert "Candidate stated expectation" in report.evidence_sources


# ---------------------------------------------------------------------------
# Copilot integration (Module 13)
# ---------------------------------------------------------------------------


def test_copilot_routes_compensation_questions():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Why are we offering this compensation?",
        "Generate compensation report",
        "Show offer justification",
        "Create finance approval report",
        "Explain executive reasoning",
        "What is the negotiation strategy?",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.COMPENSATION_GOVERNANCE


def test_copilot_compensation_intent_selects_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.COMPENSATION_GOVERNANCE) == ["compensation_governance"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Create an interview plan": Intent.GENERATE_INTERVIEW_PLAN,
        "Generate interview": Intent.INTERVIEW_STUDIO,
        "Generate executive report": Intent.EXECUTIVE_REPORT,
        "Create interview packet": Intent.EXECUTIVE_REPORT,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
        "Review this resume": Intent.RESUME_REVIEW,
        "Analyze this JD": Intent.JD_ANALYSIS,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_compensation_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Why are we offering this compensation to CAND_0000001?", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.COMPENSATION_GOVERNANCE
    assert "compensation_governance" in [t["name"] for t in turn.tools_used]
    assert "Compensation Governance" in turn.evidence_sources
    assert turn.answer
