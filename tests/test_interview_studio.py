"""Tests for the Enterprise AI Interview Studio (Phase 4 / Milestone 5).

Covers the interview-studio pipeline end-to-end — the schema (score-free), the
deterministic composer, the strategy/planner/question/rubric/decision engines,
the assembly engine (which consumes existing committee/insight outputs), the role
detection, the visualizations, automatic registration (AI platform + composer +
orchestration), safety/provenance and copilot delegation — all offline with
synthetic candidates (no dataset, no provider, no LLM).
"""

from __future__ import annotations

import json

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.agents.interview_studio import question_generator as questions_mod
from src.ai.agents.interview_studio import strategy as strategy_mod
from src.ai.agents.interview_studio import validators
from src.ai.agents.interview_studio.agent import (
    InterviewStudioInput,
    build_interview_evidence,
)
from src.ai.agents.interview_studio.composer import compose_interview_narrative
from src.ai.agents.interview_studio.report import InterviewStudioEngine
from src.ai.agents.interview_studio.schemas import (
    InterviewStudioNarrative,
    InterviewStudioReport,
)
from src.ai.agents.interview_studio.templates import (
    detect_role,
    get_depth,
    get_role,
)
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard

JD = """Senior Machine Learning Engineer
What you'll do
- Design and own scalable ML systems in production
- Lead and mentor engineers
Requirements
- 8+ years experience
- Python, PyTorch, AWS, Kubernetes, LLMs
"""


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _report(jd: str = JD, **kw) -> InterviewStudioReport:
    engine = InterviewStudioEngine(ai_runner=_runner())
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
    assert registry.has("interview_studio")


def test_composer_registered():
    assert has_composer(InterviewStudioNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("interview_studio")
    assert any(a.descriptor.name == "interview_studio" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(InterviewStudioNarrative)


def test_narrative_top_level_has_no_score_fields():
    for name in InterviewStudioNarrative.field_names():
        assert not any(tok in name.lower() for tok in ("score", "rating", "percent"))


# ---------------------------------------------------------------------------
# Composer (offline reasoning) — restates, never invents
# ---------------------------------------------------------------------------


def test_composer_uses_committee_recommendation_when_present():
    evidence = {
        "candidate_overview": {
            "title": "Senior ML Engineer",
            "company": "Acme",
            "years_of_experience": 9,
        },
        "role_name": "ML Engineer",
        "depth": "deep",
        "committee": {
            "consensus": {"recommendation": "Hire", "level": "Strong"},
            "confidence": {"overall": 80.0},
            "decision": {"interview_priorities": ["Probe ML systems depth"]},
        },
        "interview": {"technical_topics": ["Depth in PyTorch"]},
    }
    out = compose_interview_narrative(evidence)
    assert "AI Hiring Committee" in out["interview_summary"]
    assert out["readiness_label"] == "Ready to Interview"
    assert "Probe ML systems depth" in out["key_probes"]


def test_composer_never_empty_summary_and_validates():
    out = compose_interview_narrative({})
    assert out["interview_summary"].strip()
    # Composer output must validate against the schema.
    InterviewStudioNarrative(**out)


def test_composer_flags_high_risk_readiness():
    out = compose_interview_narrative(
        {
            "risk": {"risk_level": "High", "red_flags": ["Employment gap"]},
            "interview": {"technical_topics": ["x"]},
        }
    )
    assert out["readiness_label"] == "Ready — Validate Risks"
    assert "Employment gap" in out["watch_areas"]


def test_build_evidence_packs_all_sources():
    payload = InterviewStudioInput(candidate_id="C1", intelligence={"technical_score": 80})
    evidence = build_interview_evidence(payload)
    for key in (
        "committee",
        "resume",
        "jd",
        "intelligence",
        "timeline",
        "risk",
        "recommendation",
        "interview",
    ):
        assert key in evidence


# ---------------------------------------------------------------------------
# Role detection (Module 5)
# ---------------------------------------------------------------------------


def test_detect_role_specific_over_generic():
    assert detect_role("Senior Backend Engineer").key == "backend"
    assert detect_role("Machine Learning Engineer").key == "ml_engineer"
    assert detect_role("Engineering Manager").key == "engineering_manager"
    assert detect_role("Frontend Developer").key == "frontend"
    assert detect_role("Site Reliability Engineer").key == "devops"


def test_detect_role_falls_back_to_generalist():
    assert detect_role("").key == "generalist"
    assert detect_role("Astronaut").key == "generalist"


def test_get_role_and_depth_fallback():
    assert get_role("nonexistent").key == "generalist"
    assert get_depth("nonexistent").key == "standard"


# ---------------------------------------------------------------------------
# Engine — consumes existing intelligence, assembles a unified package
# ---------------------------------------------------------------------------


def test_engine_produces_unified_package():
    report = _report()
    assert isinstance(report, InterviewStudioReport)
    assert report.narrative.interview_summary
    assert report.strategy.objectives
    assert report.roadmap
    assert report.technical_questions
    assert report.behavioral_questions
    assert report.role_specific_questions
    assert report.rubrics
    assert report.decision_matrix.bands
    assert [b.label for b in report.decision_matrix.bands] == [
        "Strong Hire",
        "Hire",
        "Hold",
        "Reject",
    ]


def test_engine_detects_ml_role_from_title():
    report = _report()
    assert report.role == "ml_engineer"
    assert report.role_name == "ML Engineer"


def test_engine_explicit_role_overrides_detection():
    report = _report(role="backend")
    assert report.role == "backend"


def test_engine_integrates_committee():
    report = _report()
    assert "AI Hiring Committee" in report.evidence_sources
    assert report.decision_matrix.committee_alignment


def test_engine_consumes_many_sources():
    report = _report()
    assert len(report.evidence_sources) >= 6


def test_engine_is_deterministic():
    r1 = _report(candidate_id="CAND_DET")
    r2 = _report(candidate_id="CAND_DET")
    assert r1.role == r2.role
    assert r1.strategy.depth == r2.strategy.depth
    assert [q.text for q in r1.technical_questions] == [q.text for q in r2.technical_questions]


def test_engine_degrades_without_jd():
    report = _report(jd="")
    assert report.narrative.interview_summary
    assert any("JD" in w for w in report.warnings)


def test_engine_without_committee():
    engine = InterviewStudioEngine(ai_runner=_runner())
    report = engine.build(
        candidate=make_candidate(), jd=JD, run_committee=False, generated_on="2026-07-15"
    )
    assert report.narrative.interview_summary
    assert report.decision_matrix.bands


def test_report_to_dict_is_serializable():
    assert json.dumps(_report().to_dict())


# ---------------------------------------------------------------------------
# Personalization (Module 2) — never a generic interview
# ---------------------------------------------------------------------------


def test_senior_gets_deep_loop_with_system_design():
    report = _report()  # 9-year candidate -> deep loop
    assert report.strategy.depth == "deep"
    stage_names = [s.name for s in report.roadmap]
    assert "System Design" in stage_names
    assert any(q.category == "system_design" for q in report.technical_questions)


def test_junior_gets_lighter_loop():
    engine = InterviewStudioEngine(ai_runner=_runner())
    junior = make_candidate(
        candidate_id="CAND_JR", years=2.0, title="Software Engineer", skills=["Python", "Django"]
    )
    report = engine.build(
        candidate=junior, jd="Backend Engineer. Python.", generated_on="2026-07-15"
    )
    # Junior standard loop should be shorter than a senior deep loop.
    assert report.strategy.length_minutes <= 240


def test_question_difficulty_progression():
    report = _report()
    diffs = {q.difficulty for q in report.technical_questions}
    assert diffs <= {"Warm-up", "Core", "Deep", "Stretch"}


def test_every_question_has_a_source():
    report = _report()
    for q in report.all_questions():
        assert q.source
        assert q.text


# ---------------------------------------------------------------------------
# Risk validation (Module 6) — Risk -> Question -> Evidence -> Pass Criteria
# ---------------------------------------------------------------------------


def test_risk_validation_chain_complete():
    report = _report()
    assert report.risk_validations
    for rv in report.risk_validations:
        assert rv.risk
        assert rv.validation_question
        assert rv.expected_evidence
        assert rv.pass_criteria
        assert rv.source


def test_risk_validation_from_committee_concerns():
    evidence = {
        "committee": {
            "decision": {
                "hiring_risks": ["Unproven at scale"],
                "remaining_unknowns": ["Team-lead scope"],
            }
        },
    }
    validations = questions_mod.risk_validations(evidence)
    risks = [v.risk for v in validations]
    assert "Unproven at scale" in risks
    assert "Team-lead scope" in risks
    assert any(v.category == "committee" for v in validations)


# ---------------------------------------------------------------------------
# Rubrics (Module 7) + Strategy (Module 1)
# ---------------------------------------------------------------------------


def test_rubrics_cover_all_core_dimensions():
    report = _report()
    names = {d.name for d in report.rubrics}
    for expected in (
        "Technical Depth",
        "Communication",
        "Leadership",
        "Ownership",
        "Collaboration",
        "Decision Making",
        "Problem Solving",
        "Architecture",
    ):
        assert expected in names
    for dim in report.rubrics:
        assert set(dim.levels) == {"Strong", "Solid", "Mixed", "Weak"}


def test_strategy_priorities_follow_committee():
    evidence = {
        "candidate_overview": {"years_of_experience": 9},
        "committee": {"decision": {"interview_priorities": ["Validate distributed systems depth"]}},
    }
    strat = strategy_mod.build_strategy(evidence, get_role("backend"))
    assert "Validate distributed systems depth" in strat.priorities


# ---------------------------------------------------------------------------
# Safety / provenance (Module 16)
# ---------------------------------------------------------------------------


def test_provenance_every_statement_attributed():
    report = _report()
    assert report.provenance
    for entry in report.provenance:
        assert entry.source
        assert entry.kind in validators.ALLOWED_KINDS
        assert entry.statement
    assert validators.validate_provenance(report.provenance) == []


def test_provenance_separates_registers():
    report = _report()
    kinds = {p.kind for p in report.provenance}
    assert "Evidence" in kinds
    assert "Recommendation" in kinds
    assert kinds <= set(validators.ALLOWED_KINDS)


# ---------------------------------------------------------------------------
# Visualizations (Module 12)
# ---------------------------------------------------------------------------


def test_chart_data_built_for_every_visual():
    report = _report()
    for key in (
        "timeline",
        "coverage_radar",
        "risk_heatmap",
        "question_distribution",
        "difficulty_distribution",
        "decision_readiness",
        "rubric_weights",
    ):
        assert key in report.charts


def test_chart_data_is_pure_and_bounded():
    report = _report()
    assert 0.0 <= report.charts["decision_readiness"] <= 1.0
    total = sum(report.charts["question_distribution"].values())
    assert total == len(report.all_questions())
    assert report.charts["total_minutes"] == sum(s.duration_minutes for s in report.roadmap)


# ---------------------------------------------------------------------------
# Copilot integration (Module 13)
# ---------------------------------------------------------------------------


def test_copilot_routes_interview_studio_questions():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Generate interview",
        "Create a backend interview",
        "Interview this ML Engineer",
        "What questions validate the committee concerns?",
        "Generate interviewer packet",
        "Show me the evaluation rubric and decision matrix",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.INTERVIEW_STUDIO


def test_copilot_interview_studio_intent_selects_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.INTERVIEW_STUDIO) == ["interview_studio"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Create an interview plan": Intent.GENERATE_INTERVIEW_PLAN,
        "Analyze this candidate in detail": Intent.ANALYZE_CANDIDATE,
        "Find machine learning engineers": Intent.SEARCH_CANDIDATE,
        "Review this resume": Intent.RESUME_REVIEW,
        "Analyze this JD": Intent.JD_ANALYSIS,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
        "Generate executive report": Intent.EXECUTIVE_REPORT,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_interview_studio_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Generate a backend interview for CAND_0000001", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.INTERVIEW_STUDIO
    assert "interview_studio" in [t["name"] for t in turn.tools_used]
    assert "Interview Studio" in turn.evidence_sources
    assert turn.answer


def test_tool_routes_role_and_depth():
    from src.ai.tools.interview_studio_tools import route_request

    assert route_request("create a backend interview")["role"] == "backend"
    assert route_request("full loop interview")["depth"] == "deep"
    assert route_request("quick phone screen")["depth"] == "screen"
    # A generic phrase must not force a role (keeps it auto-detected).
    assert route_request("generate an interview")["role"] == ""


def test_tool_registered_in_builtin():
    import src.ai.tools.builtin  # noqa: F401  (populates the registry)
    from src.ai.tools.registry import registry as tool_registry

    assert tool_registry.has("interview_studio")
