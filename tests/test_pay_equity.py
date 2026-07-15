"""Tests for the Enterprise Pay Equity Guardian (Phase 5 / Milestone 2).

Covers the equity pipeline end-to-end — the score-free schema, the deterministic
composer, compression / inversion / promotion / policy / risk / executive-review
modules, the HRIS-provider interface (default-unavailable + injected path), the
engine assembly (reusing the Compensation Governance offer), scenario simulation,
safety/no-fabrication + no-legal-conclusion guarantees, automatic registration and
copilot delegation — all offline with synthetic candidates.
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

from src.ai.agents.pay_equity.agent import (
    PayEquityInput,
    build_pay_equity_evidence,
    pay_equity_agent,
)
from src.ai.agents.pay_equity.equity_engine import (
    NullPayEquityDataProvider,
    PayEquityGuardianEngine,
    build_equity_findings,
)
from src.ai.agents.pay_equity.composer import compose_pay_equity_narrative
from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    EquityRisk,
    InversionAssessment,
    PayEquityNarrative,
    PayEquityReport,
)
from src.ai.agents.pay_equity import compression as compression_mod
from src.ai.agents.pay_equity import inversion as inversion_mod
from src.ai.agents.pay_equity import policy as policy_mod
from src.ai.agents.pay_equity import risk as risk_mod
from src.ai.agents.pay_equity import review as review_mod
from src.ai.agents.pay_equity import validators
from src.ai.agents.pay_equity.templates import get_policy

from src.ai.orchestration.registry.agent_registry import orchestration_registry

JD = "Senior Machine Learning Engineer. Python, PyTorch, AWS, Kubernetes, LLMs. 8+ years. Lead and mentor."


class _StubProvider:
    """An injected HRIS provider stub for the data-available path (Module 12)."""

    def __init__(self, peers=None, band=None):
        self._peers = peers if peers is not None else [
            {"employee_id": "E1", "compensation": 48.0, "tenure_years": 4, "responsibility": "senior"},
            {"employee_id": "E2", "compensation": 45.0, "tenure_years": 6, "responsibility": "senior"},
            {"employee_id": "E3", "compensation": 60.0, "tenure_years": 2, "responsibility": "senior"},
        ]
        self._band = band if band is not None else {"min": 40.0, "max": 55.0}

    def is_available(self) -> bool:
        return True

    def get_pay_band(self, role, level):
        return dict(self._band)

    def get_peers(self, role, level, department=""):
        return list(self._peers)


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _report(provider=None, **kw) -> PayEquityReport:
    engine = PayEquityGuardianEngine(ai_runner=_runner(), data_provider=provider)
    return engine.build(
        candidate=make_candidate(candidate_id=kw.pop("candidate_id", "CAND_1")),
        jd=kw.pop("jd", JD),
        generated_on="2026-07-15",
        **kw,
    )


def _ctx(target=50.0):
    return {
        "role": "ML Engineer",
        "level": "senior",
        "offer": {"minimum": 45, "target": target, "maximum": 58, "currency": "INR", "unit": "LPA"},
        "market_position": "Market Competitive",
        "hire_type": "Growth Hire",
    }


# ---------------------------------------------------------------------------
# Registration + schema
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("pay_equity_guardian")


def test_composer_registered():
    assert has_composer(PayEquityNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("pay_equity")
    assert any(a.descriptor.name == "pay_equity_guardian" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(PayEquityNarrative)


def test_tool_registered_in_builtin():
    from src.ai.tools.registry import registry as tool_registry
    import src.ai.tools.builtin  # noqa: F401

    assert tool_registry.has("pay_equity_guardian")


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def test_composer_never_empty_and_validates():
    out = compose_pay_equity_narrative({})
    assert out["executive_summary"].strip()
    PayEquityNarrative(**out)


def test_composer_states_data_unavailable():
    out = compose_pay_equity_narrative({"data_available": False})
    assert "unavailable" in out["data_availability_note"].lower()
    assert "unable to evaluate" in out["inversion_note"].lower()


def test_build_evidence_packs_all_sections():
    payload = PayEquityInput(candidate_id="C1")
    ev = build_pay_equity_evidence(payload)
    for key in ("offer_summary", "compression", "inversion", "policy_alignment",
                "fairness", "executive_review", "equity_risk", "data_available"):
        assert key in ev


# ---------------------------------------------------------------------------
# Module 2 — Compression (data-gated)
# ---------------------------------------------------------------------------


def test_compression_unavailable_without_data():
    c = compression_mod.assess_compression(_ctx(), NullPayEquityDataProvider())
    assert c.risk_level == "Unavailable"
    assert c.data_available is False
    assert "unavailable" in c.rationale.lower()


def test_compression_detected_with_data():
    c = compression_mod.assess_compression(_ctx(target=50.0), _StubProvider())
    assert c.data_available is True
    assert c.risk_level in ("Low", "Medium", "High")
    # Two peers (45, 48) sit below the 50 target with tenure -> compression present.
    assert c.risk_level in ("Medium", "High")
    assert c.evidence


# ---------------------------------------------------------------------------
# Module 3 — Inversion (data-gated)
# ---------------------------------------------------------------------------


def test_inversion_unavailable_without_data():
    i = inversion_mod.assess_inversion(_ctx(), NullPayEquityDataProvider())
    assert i.risk_level == "Unavailable"
    assert "unable to evaluate" in i.rationale.lower()


def test_inversion_detected_with_data():
    i = inversion_mod.assess_inversion(_ctx(target=50.0), _StubProvider())
    assert i.data_available is True
    # E1(48) + E2(45) are senior-responsibility peers below the 50 target.
    assert i.risk_level in ("Medium", "High")
    assert i.cases


# ---------------------------------------------------------------------------
# Module 5 — Policy alignment (configurable, never hardcoded)
# ---------------------------------------------------------------------------


def test_policy_not_evaluable_without_data():
    comp = CompressionAssessment()
    inv = InversionAssessment()
    pa = policy_mod.evaluate_policy(get_policy("pay_band_first"), _ctx(), comp, inv)
    assert pa.alignment == "Not Evaluable"


def test_policy_flags_review_on_compression():
    comp = compression_mod.assess_compression(_ctx(target=50.0), _StubProvider())
    inv = inversion_mod.assess_inversion(_ctx(target=50.0), _StubProvider())
    pa = policy_mod.evaluate_policy(get_policy("pay_band_first"), _ctx(), comp, inv)
    assert pa.alignment in ("Partial", "Violation")
    assert pa.violations


# ---------------------------------------------------------------------------
# Risk + executive review (Module 7)
# ---------------------------------------------------------------------------


def test_equity_risk_unknown_without_data():
    er = risk_mod.build_equity_risk(CompressionAssessment(), InversionAssessment(), policy_mod.evaluate_policy(
        get_policy("pay_band_first"), _ctx(), CompressionAssessment(), InversionAssessment()))
    assert er.level == "Unknown"
    assert er.data_available is False


def test_executive_review_escalates_on_high_risk():
    comp = compression_mod.assess_compression(_ctx(target=50.0), _StubProvider())
    inv = inversion_mod.assess_inversion(_ctx(target=50.0), _StubProvider())
    pa = policy_mod.evaluate_policy(get_policy("pay_band_first"), _ctx(), comp, inv)
    er = risk_mod.build_equity_risk(comp, inv, pa)
    review = review_mod.build_executive_review(_ctx(), er, comp, inv, pa)
    # Inversion detected -> Legal review; high risk -> Executive review.
    assert "Legal" in review.required_approvers()
    assert review.review_level in ("Elevated", "Executive")


def test_baseline_approvers_always_present():
    review = review_mod.build_executive_review(
        _ctx(), EquityRisk(level="Unknown"), CompressionAssessment(), InversionAssessment(),
        policy_mod.evaluate_policy(get_policy("pay_band_first"), _ctx(), CompressionAssessment(), InversionAssessment()),
    )
    for approver in ("Recruiter", "Hiring Manager", "HR"):
        assert approver in review.required_approvers()


# ---------------------------------------------------------------------------
# Module 1 — Internal equity findings
# ---------------------------------------------------------------------------


def test_equity_findings_not_evaluable_without_data():
    findings = build_equity_findings(_ctx(), NullPayEquityDataProvider())
    assert len(findings) == 7
    assert all(f.status == "Not Evaluable" for f in findings)
    assert all(f.register == "Unavailable Data" for f in findings)


def test_equity_findings_evaluated_with_data():
    findings = build_equity_findings(_ctx(target=50.0), _StubProvider())
    assert len(findings) == 7
    assert any(f.register == "Observed Evidence" for f in findings)


# ---------------------------------------------------------------------------
# Engine — reuses compensation, assembles the report
# ---------------------------------------------------------------------------


def test_engine_produces_report_without_internal_data():
    report = _report()
    assert isinstance(report, PayEquityReport)
    assert report.data_available is False
    assert report.equity_risk.level == "Unknown"
    assert report.compression.risk_level == "Unavailable"
    assert report.inversion.risk_level == "Unavailable"
    assert report.narrative.executive_summary
    # Reused the compensation governance offer.
    assert report.offer_summary.get("recommended_range")
    assert "Compensation Governance Agent" in report.evidence_sources


def test_engine_produces_report_with_internal_data():
    report = _report(provider=_StubProvider(), candidate_id="CAND_2")
    assert report.data_available is True
    assert report.equity_risk.level in ("Low", "Medium", "High")
    assert report.compression.risk_level in ("Low", "Medium", "High")
    assert report.executive_review.required_approvers()


def test_engine_is_deterministic():
    r1 = _report(candidate_id="CAND_DET")
    r2 = _report(candidate_id="CAND_DET")
    assert r1.equity_risk.level == r2.equity_risk.level
    assert r1.offer_summary["target"] == r2.offer_summary["target"]


def test_engine_scenarios_present():
    report = _report()
    names = [s.name for s in report.scenarios]
    assert names == ["Current Offer", "Equity-Optimized Offer", "Competitive-Win Offer"]


def test_report_to_dict_is_serializable():
    assert json.dumps(_report().to_dict())
    assert json.dumps(_report(provider=_StubProvider(), candidate_id="CAND_J").to_dict())


# ---------------------------------------------------------------------------
# Safety (Module 14)
# ---------------------------------------------------------------------------


def test_no_legal_or_discrimination_language():
    report = _report(provider=_StubProvider(), candidate_id="CAND_S")
    warnings = validators.validate_safety(
        report.narrative, report.compression, report.inversion, report.equity_risk, report.data_available
    )
    assert warnings == []


def test_narrative_never_scores_or_accuses():
    report = _report(provider=_StubProvider(), candidate_id="CAND_S2")
    blob = " ".join(v for v in report.narrative.to_dict().values() if isinstance(v, str)).lower()
    for forbidden in ("discriminates against", "is discriminatory", "illegal", "lawsuit", "guilty of"):
        assert forbidden not in blob


def test_charts_present():
    report = _report(provider=_StubProvider(), candidate_id="CAND_C")
    for key in ("equity_risk_gauge", "compression_matrix", "approval_flow",
                "offer_alignment", "governance_status", "scenario_comparison", "executive_review_pipeline"):
        assert key in report.charts


# ---------------------------------------------------------------------------
# Copilot integration (Module 11)
# ---------------------------------------------------------------------------


def test_copilot_routes_pay_equity_questions():
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState
    from src.ai.copilot.models import Intent

    clf = IntentClassifier()
    for message in [
        "Is this offer fair?",
        "Check internal equity",
        "Show compression risk",
        "Who should approve this?",
        "Does this violate pay policy?",
        "Generate pay equity report",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.PAY_EQUITY


def test_copilot_pay_equity_intent_selects_tool():
    from src.ai.copilot.tool_selector import select_tools
    from src.ai.copilot.models import Intent

    assert select_tools(Intent.PAY_EQUITY) == ["pay_equity_guardian"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState
    from src.ai.copilot.models import Intent

    clf = IntentClassifier()
    cases = {
        "Why are we offering this compensation?": Intent.COMPENSATION_GOVERNANCE,
        "Generate compensation report": Intent.COMPENSATION_GOVERNANCE,
        "What is the negotiation strategy?": Intent.COMPENSATION_GOVERNANCE,
        "Generate interview": Intent.INTERVIEW_STUDIO,
        "Create an interview plan": Intent.GENERATE_INTERVIEW_PLAN,
        "Generate executive report": Intent.EXECUTIVE_REPORT,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_pay_equity_end_to_end():
    from src.ai.tools.provider import InMemoryCandidateRepository
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Is this offer fair for CAND_0000001?", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.PAY_EQUITY
    assert "pay_equity_guardian" in [t["name"] for t in turn.tools_used]
    assert "Pay Equity Guardian" in turn.evidence_sources
    assert turn.answer


def test_tool_routes_policy():
    from src.ai.tools.pay_equity_tools import route_policy

    assert route_policy("check this under market first policy") == "market_first"
    assert route_policy("no policy named") == ""
