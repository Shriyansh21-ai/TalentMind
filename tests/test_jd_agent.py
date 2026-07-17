"""Tests for the JDAnalystAgent (Phase 4 / Milestone 2).

Covers JD parsing, role/technical/hiring-intent/organization analysis, the
requirement hierarchy, market heuristics, evidence-only risk detection, the
structured schema + safety, automatic registration (AI platform + orchestration),
and copilot auto-delegation — all offline (no dataset, no provider, no LLM).
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from src.ai.agents.jd import extractors, validators
from src.ai.agents.jd.agent import JDAnalystInput, jd_analyst_agent
from src.ai.agents.jd.metrics import compute_metrics, market_estimates
from src.ai.agents.jd.schemas import JDAnalysis
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard

SAMPLE_JD = """Senior Machine Learning Engineer
Department: AI Platform
Location: Remote (US)
Employment Type: Full-time

About Us
We are a fast-paced Series B startup building a generative AI platform.

What you'll do
- Design and own scalable ML systems in production serving millions of requests
- Lead and mentor a small team of engineers
- Partner with product and stakeholders across functions

Requirements
- 8+ years of experience in software engineering
- Strong Python and experience with PyTorch and LLMs
- Must have experience with AWS, Kubernetes and distributed systems

Nice to have
- Experience with Rust
- Familiarity with Terraform and GraphQL

Benefits
- Equity, health insurance, unlimited PTO
"""


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


# ---------------------------------------------------------------------------
# Extraction (Module 1)
# ---------------------------------------------------------------------------


def test_extraction_parses_sections():
    doc = extractors.extract(SAMPLE_JD)
    assert doc.title.startswith("Senior Machine Learning Engineer")
    assert doc.responsibilities and doc.requirements and doc.preferred
    assert doc.years_experience == 8
    assert doc.remote_policy == "remote"
    assert "requirements" in doc.sections_present
    assert "responsibilities" in doc.sections_present


def test_extraction_no_compensation_when_absent():
    # The sample JD has benefits but no salary → compensation must stay empty
    # (never invented — Module 17).
    doc = extractors.extract(SAMPLE_JD)
    assert doc.compensation == ""
    assert "compensation" in doc.sections_empty


# ---------------------------------------------------------------------------
# Metrics (Modules 3, 7, 9, 11)
# ---------------------------------------------------------------------------


def test_metrics_technology_categorization():
    m = compute_metrics(extractors.extract(SAMPLE_JD))
    assert "python" in m.languages
    assert "aws" in m.cloud
    assert "kubernetes" in m.devops
    assert set(m.ai_ml) & {"pytorch", "llm", "ml", "machine learning"}


def test_metrics_no_substring_false_positive():
    # "scalable" must NOT register the language "scala".
    m = compute_metrics(extractors.extract("We build scalable systems."))
    assert "scala" not in m.languages


def test_metrics_dimensions_bounded_and_complete():
    m = compute_metrics(extractors.extract(SAMPLE_JD))
    for name in [
        "overall",
        "structure",
        "technical_clarity",
        "role_clarity",
        "requirement_quality",
        "business_context",
        "hiring_readiness",
        "market_alignment",
        "organization_clarity",
    ]:
        assert name in m.dimensions
        assert 0.0 <= m.dimensions[name] <= 100.0


def test_market_estimates_have_confidence_and_never_invent_salary():
    doc = extractors.extract(SAMPLE_JD)  # no compensation in the JD
    estimates = market_estimates(doc, compute_metrics(doc))
    assert all("confidence" in e for e in estimates)
    salary = next(e for e in estimates if e["dimension"] == "salary_competitiveness")
    assert "cannot assess" in salary["assessment"].lower()


# ---------------------------------------------------------------------------
# Risk validation (Module 8) — evidence only
# ---------------------------------------------------------------------------


def test_risk_flags_missing_compensation_and_broad_stack():
    doc = extractors.extract(SAMPLE_JD)
    findings = validators.detect_risks(doc, compute_metrics(doc))
    types = {f.type for f in findings}
    assert "missing_compensation" in types
    assert all(f.evidence for f in findings)  # every finding cites evidence


def test_risk_flags_conflicting_seniority():
    jd = "Junior Software Engineer\nRequirements\n- 10+ years of experience required"
    doc = extractors.extract(jd)
    findings = validators.detect_risks(doc, compute_metrics(doc))
    assert any(f.type == "conflicting_requirements" for f in findings)


def test_risk_flags_missing_requirements_and_responsibilities():
    doc = extractors.extract("Software Engineer\nWe are hiring.")
    findings = validators.detect_risks(doc, compute_metrics(doc))
    types = {f.type for f in findings}
    assert "missing_responsibilities" in types or "missing_evaluation_criteria" in types


def test_risk_flags_hiring_bias():
    jd = "Engineer\nRequirements\n- Looking for a young energetic rockstar ninja"
    doc = extractors.extract(jd)
    findings = validators.detect_risks(doc, compute_metrics(doc))
    assert any(f.type == "hiring_bias" for f in findings)


# ---------------------------------------------------------------------------
# Schema + safety (Module 12, 17)
# ---------------------------------------------------------------------------


def test_schema_is_score_free_at_top_level():
    SafetyGuard().assert_schema_is_score_free(JDAnalysis)


def test_schema_top_level_fields_present():
    fields = set(JDAnalysis.field_names())
    for expected in [
        "executive_summary",
        "role_intelligence",
        "technical_intelligence",
        "hiring_intent",
        "organization_intelligence",
        "requirement_hierarchy",
        "market_intelligence",
        "quality",
        "structure",
        "risk_report",
        "improvement_plan",
        "confidence_note",
        "evidence",
    ]:
        assert expected in fields


# ---------------------------------------------------------------------------
# Registration (final requirements)
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("jd_analyst")


def test_composer_registered_for_offline_reasoning():
    assert has_composer(JDAnalysis.schema_name())


def test_agent_registered_with_orchestration_platform():
    found = orchestration_registry.discover("jd_analysis")
    assert any(a.descriptor.name == "jd_analyst" for a in found)


# ---------------------------------------------------------------------------
# End-to-end agent run (offline)
# ---------------------------------------------------------------------------


def test_agent_produces_valid_analysis():
    result = _runner().run(jd_analyst_agent, JDAnalystInput(jd_text=SAMPLE_JD, jd_id="JD_1"))
    assert result.ok
    assert result.provider == "local"
    a = result.data
    assert isinstance(a, JDAnalysis)
    assert a.executive_summary
    assert 0 <= a.quality.overall <= 100
    assert a.improvement_plan
    assert a.evidence


def test_agent_infers_senior_role_and_confidence():
    a = _runner().run(jd_analyst_agent, JDAnalystInput(jd_text=SAMPLE_JD)).data
    assert a.role_intelligence.seniority == "Senior+"
    assert a.role_intelligence.confidence > 0


def test_agent_every_hiring_intent_signal_has_confidence():
    a = _runner().run(jd_analyst_agent, JDAnalystInput(jd_text=SAMPLE_JD)).data
    assert a.hiring_intent.signals
    assert all(s.confidence > 0 for s in a.hiring_intent.signals)


def test_agent_requirement_hierarchy_splits_mandatory_preferred():
    a = _runner().run(jd_analyst_agent, JDAnalystInput(jd_text=SAMPLE_JD)).data
    assert a.requirement_hierarchy.mandatory
    assert a.requirement_hierarchy.preferred
    # "Rust" is under "Nice to have" → preferred, not mandatory.
    joined_pref = " ".join(a.requirement_hierarchy.preferred).lower()
    assert "rust" in joined_pref


def test_agent_improvements_priority_ordered():
    a = _runner().run(jd_analyst_agent, JDAnalystInput(jd_text=SAMPLE_JD)).data
    rank = {"high": 0, "medium": 1, "low": 2}
    priorities = [rank.get(i.priority, 3) for i in a.improvement_plan]
    assert priorities == sorted(priorities)


# ---------------------------------------------------------------------------
# Copilot integration (Module 14) — automatic delegation
# ---------------------------------------------------------------------------


def test_copilot_routes_jd_questions_to_jd_analysis():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Analyze this JD",
        "What level is this role?",
        "Is this JD well written?",
        "Is the hiring expectation realistic?",
        "What skills are actually mandatory?",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.JD_ANALYSIS


def test_copilot_jd_intent_selects_jd_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.JD_ANALYSIS) == ["jd_analysis"]


def test_copilot_existing_and_resume_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Analyze this candidate in detail": Intent.ANALYZE_CANDIDATE,
        "Compare CAND_0000001 and CAND_0000002": Intent.COMPARE_CANDIDATES,
        "Find machine learning engineers": Intent.SEARCH_CANDIDATE,
        "Review this resume": Intent.RESUME_REVIEW,
        "Is this resume ATS friendly?": Intent.RESUME_REVIEW,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_jd_agent_end_to_end():
    from conftest import make_candidate

    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository([make_candidate(candidate_id="CAND_0000001")])
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Analyze this JD", jd=SAMPLE_JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.JD_ANALYSIS
    assert "jd_analysis" in [t["name"] for t in turn.tools_used]
    assert "JD Analyst Agent" in turn.evidence_sources
    assert turn.answer


def test_copilot_jd_analysis_without_jd_is_graceful():
    from conftest import make_candidate

    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository([make_candidate()])
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Analyze this JD")  # no JD attached
    # Tool fails gracefully; the copilot still produces an answer, no crash.
    assert turn.answer
    jd_tool = next((t for t in turn.tools_used if t["name"] == "jd_analysis"), None)
    assert jd_tool is not None and jd_tool["ok"] is False
