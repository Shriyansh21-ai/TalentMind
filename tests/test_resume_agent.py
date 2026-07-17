"""Tests for the ResumeAnalystAgent (Phase 4 / Milestone 1).

Covers extraction, metrics, risk validation, the structured schema + safety,
the end-to-end agent run (offline), automatic registration with the AI platform
and orchestration registry, and copilot auto-delegation — all offline with
synthetic candidates (no dataset, no FAISS, no provider, no LLM).
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.agents.resume import extractors, validators
from src.ai.agents.resume.agent import (
    ResumeAnalystInput,
    resume_analyst_agent,
)
from src.ai.agents.resume.extractors import ResumeDocument, ResumeExperience
from src.ai.agents.resume.metrics import compute_metrics
from src.ai.agents.resume.schemas import ResumeAnalysis
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


# ---------------------------------------------------------------------------
# Extraction (Module 1)
# ---------------------------------------------------------------------------


def test_extraction_from_candidate_populates_sections():
    doc = extractors.extract(make_candidate())
    assert doc.summary
    assert doc.experiences and doc.skills
    assert "work_experience" in doc.sections_present
    assert "skills" in doc.sections_present
    assert doc.bullets  # experience descriptions split into bullets


def test_extraction_detects_projects_from_descriptions():
    doc = extractors.extract(make_candidate())
    # The default candidate's history mentions "Led ML platform / Built ..." →
    # project-like statements should be detected.
    assert doc.projects
    assert any("led" in p.text.lower() or "built" in p.text.lower() for p in doc.projects)


# ---------------------------------------------------------------------------
# Metrics (Modules 2, 4, 6, 7, 11)
# ---------------------------------------------------------------------------


def test_metrics_dimensions_are_bounded_and_complete():
    doc = extractors.extract(make_candidate())
    m = compute_metrics(doc, jd="python machine learning aws")
    for name in [
        "overall",
        "structure",
        "writing",
        "technical_depth",
        "project_quality",
        "achievements",
        "ats_friendliness",
        "professionalism",
        "career_narrative",
    ]:
        assert name in m.dimensions
        assert 0.0 <= m.dimensions[name] <= 100.0


def test_metrics_technical_categorization():
    doc = extractors.extract(make_candidate())  # ML/LLM/AWS/PyTorch stack
    m = compute_metrics(doc)
    assert m.ai_exposure is True
    assert m.cloud_exposure is True
    assert "python" in m.modern_tech


def test_metrics_ats_matches_jd_keywords():
    doc = extractors.extract(make_candidate())
    m = compute_metrics(doc, jd="python kubernetes terraform")
    # Candidate has python but not kubernetes/terraform → those are missing.
    assert "kubernetes" in m.missing_keywords or "terraform" in m.missing_keywords


def test_metrics_detects_buzzwords():
    doc = ResumeDocument(candidate_id="C")
    doc.experiences = [
        ResumeExperience(
            company="X",
            title="Engineer",
            description="Passionate results-driven rockstar ninja.",
            bullets=["Passionate results-driven rockstar ninja"],
        )
    ]
    doc.bullets = ["Passionate results-driven rockstar ninja"]
    m = compute_metrics(doc)
    assert len(m.buzzword_hits) >= 3


# ---------------------------------------------------------------------------
# Risk validation (Module 8) — evidence only
# ---------------------------------------------------------------------------


def test_risk_detects_multiple_current_roles():
    doc = ResumeDocument(candidate_id="C")
    doc.experiences = [
        ResumeExperience(company="A", title="Eng", start_date="2022-01-01", is_current=True),
        ResumeExperience(company="B", title="Eng", start_date="2021-01-01", is_current=True),
    ]
    findings = validators.detect_risks(doc, compute_metrics(doc))
    assert any(f.type == "contradiction" for f in findings)
    # Every finding must carry concrete evidence (never hallucinated).
    assert all(f.evidence for f in findings)


def test_risk_detects_employment_gap():
    doc = ResumeDocument(candidate_id="C")
    doc.experiences = [
        ResumeExperience(
            company="New", title="Eng", start_date="2020-01-01", end_date="2021-01-01"
        ),
        ResumeExperience(
            company="Old", title="Eng", start_date="2015-01-01", end_date="2016-01-01"
        ),
    ]
    findings = validators.detect_risks(doc, compute_metrics(doc))
    assert any(f.type == "employment_gap" for f in findings)


def test_risk_detects_missing_dates():
    doc = ResumeDocument(candidate_id="C")
    doc.experiences = [ResumeExperience(company="A", title="Eng", start_date="", is_current=False)]
    findings = validators.detect_risks(doc, compute_metrics(doc))
    assert any(f.type == "missing_dates" for f in findings)


def test_clean_candidate_has_low_risk():
    doc = extractors.extract(make_candidate())
    findings = validators.detect_risks(doc, compute_metrics(doc))
    assert validators.risk_level(findings) in ("Low", "Low-Medium")


# ---------------------------------------------------------------------------
# Schema + safety (Module 12, 17)
# ---------------------------------------------------------------------------


def test_schema_is_score_free_at_top_level():
    # The platform safety guard must accept the schema (no top-level score field).
    SafetyGuard().assert_schema_is_score_free(ResumeAnalysis)


def test_schema_top_level_fields_present():
    fields = set(ResumeAnalysis.field_names())
    for expected in [
        "executive_summary",
        "strengths",
        "weaknesses",
        "career_story",
        "resume_quality",
        "writing",
        "technical",
        "projects",
        "achievements",
        "ats_report",
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
    assert registry.has("resume_analyst")


def test_composer_registered_for_offline_reasoning():
    assert has_composer(ResumeAnalysis.schema_name())


def test_agent_registered_with_orchestration_platform():
    found = orchestration_registry.discover("resume_analysis")
    assert any(a.descriptor.name == "resume_analyst" for a in found)


# ---------------------------------------------------------------------------
# End-to-end agent run (offline)
# ---------------------------------------------------------------------------


def test_agent_produces_valid_analysis():
    result = _runner().run(
        resume_analyst_agent,
        ResumeAnalystInput(candidate_id="CAND_X", candidate=make_candidate(), jd="python aws"),
    )
    assert result.ok
    assert result.provider == "local"
    analysis = result.data
    assert isinstance(analysis, ResumeAnalysis)
    assert analysis.executive_summary
    assert 0 <= analysis.resume_quality.overall <= 100
    assert analysis.improvement_plan  # some recommendations produced
    assert analysis.evidence  # evidence cited


def test_agent_improvements_are_priority_ordered():
    result = _runner().run(
        resume_analyst_agent,
        ResumeAnalystInput(candidate_id="CAND_X", candidate=make_candidate()),
    )
    rank = {"high": 0, "medium": 1, "low": 2}
    priorities = [rank.get(i.priority, 3) for i in result.data.improvement_plan]
    assert priorities == sorted(priorities)


def test_agent_never_fabricates_quantified_achievements():
    # A candidate whose bullets contain no numbers must yield no quantified claims.
    cand = make_candidate(summary="Engineer who builds software with teams.")
    # Strip numeric content from descriptions.
    for entry in cand.career_history:
        entry.description = "Worked on backend services and mentored peers."
    result = _runner().run(
        resume_analyst_agent, ResumeAnalystInput(candidate_id="C", candidate=cand)
    )
    assert result.data.achievements.quantified == []
    assert any(
        "quantif" in w.lower()
        for w in result.data.weaknesses + [i.title.lower() for i in result.data.improvement_plan]
    )


# ---------------------------------------------------------------------------
# Copilot integration (Module 14) — automatic delegation, no manual routing
# ---------------------------------------------------------------------------


def test_copilot_routes_resume_questions_to_resume_review():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Review this resume",
        "What is weak?",
        "How can candidate improve?",
        "Is this resume ATS friendly?",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.RESUME_REVIEW


def test_copilot_resume_intent_selects_resume_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.RESUME_REVIEW) == ["resume_analysis"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Analyze this candidate in detail": Intent.ANALYZE_CANDIDATE,
        "Compare CAND_0000001 and CAND_0000002": Intent.COMPARE_CANDIDATES,
        "Find machine learning engineers": Intent.SEARCH_CANDIDATE,
        "Should we hire this candidate?": Intent.RECOMMENDATION_QUESTION,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_resume_agent_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Review this resume for CAND_0000001", jd="python aws")
    assert turn.status == "ok"
    assert turn.intent == Intent.RESUME_REVIEW
    assert "resume_analysis" in [t["name"] for t in turn.tools_used]
    assert "Resume Analyst Agent" in turn.evidence_sources
    assert turn.answer
