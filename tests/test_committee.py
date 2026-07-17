"""Tests for the AI Hiring Committee (Phase 4 / Milestone 3).

Covers the committee lifecycle, independent opinion generation + abstention,
evidence-weighted consensus, conflict detection, discussion, confidence metrics,
the executive decision, memory, deterministic scenario modes, automatic
registration (AI platform + orchestration) and copilot delegation — all offline
with synthetic candidates (no dataset, no provider, no LLM).
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.committee.committee import EvidenceBundle, HiringCommitteeEngine
from src.ai.committee.conflict_resolution import detect_conflicts
from src.ai.committee.consensus import build_consensus
from src.ai.committee.discussion import run_discussion
from src.ai.committee.members import build_panel
from src.ai.committee.schemas import (
    CommitteeDecision,
    CommitteeMode,
    ConsensusLevel,
    MemberOpinion,
    Recommendation,
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


def _engine() -> HiringCommitteeEngine:
    return HiringCommitteeEngine(ai_runner=_runner())


def _opinion(role, rec, conf, evidence_n=3, abstained=False) -> MemberOpinion:
    return MemberOpinion(
        role=role,
        role_title=role.title(),
        recommendation=rec,
        confidence=conf,
        opinion=f"{role} opinion",
        strengths=["s"],
        concerns=["c"],
        evidence=[f"[src] e{i}" for i in range(evidence_n)],
        evidence_sources=["Candidate Intelligence engine"],
        abstained=abstained,
    )


# ---------------------------------------------------------------------------
# Registration + schema (final requirements, Module 12/16)
# ---------------------------------------------------------------------------


def test_chair_registered_with_ai_platform():
    assert registry.has("committee_chair")


def test_chair_composer_registered():
    assert has_composer(CommitteeDecision.schema_name())


def test_committee_registered_with_orchestration():
    found = orchestration_registry.discover("hiring_committee")
    assert any(a.descriptor.name == "hiring_committee" for a in found)


def test_decision_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(CommitteeDecision)


# ---------------------------------------------------------------------------
# Consensus engine (Module 4) — evidence weighting, not majority
# ---------------------------------------------------------------------------


def test_strong_consensus_when_all_agree():
    opinions = [_opinion(f"m{i}", Recommendation.HIRE, 85) for i in range(5)]
    consensus = build_consensus(opinions, CommitteeMode.BALANCED)
    assert consensus.level == ConsensusLevel.STRONG
    assert consensus.recommendation in (Recommendation.HIRE, Recommendation.STRONG_HIRE)


def test_split_or_no_consensus_when_divided():
    opinions = [
        _opinion("a", Recommendation.HIRE, 85),
        _opinion("b", Recommendation.HIRE, 80),
        _opinion("c", Recommendation.NO_HIRE, 85),
        _opinion("d", Recommendation.NO_HIRE, 80),
    ]
    consensus = build_consensus(opinions, CommitteeMode.BALANCED)
    assert consensus.level in (ConsensusLevel.SPLIT, ConsensusLevel.NONE)


def test_evidence_weighting_beats_headcount():
    # Three low-confidence, low-evidence "No Hire" vs one very strong "Hire".
    opinions = [
        _opinion("weak1", Recommendation.NO_HIRE, 30, evidence_n=1),
        _opinion("weak2", Recommendation.NO_HIRE, 30, evidence_n=1),
        _opinion("weak3", Recommendation.LEAN_NO_HIRE, 30, evidence_n=1),
        _opinion("strong", Recommendation.HIRE, 95, evidence_n=3),
    ]
    consensus = build_consensus(opinions, CommitteeMode.BALANCED)
    # Majority is negative, but the well-evidenced positive pulls the stance up
    # relative to a pure headcount (which would be firmly negative).
    assert consensus.weighted_stance > -1.0


# ---------------------------------------------------------------------------
# Conflict detection (Module 5) — never invented
# ---------------------------------------------------------------------------


def test_conflicts_detected_for_divergent_opinions():
    opinions = [
        _opinion("a", Recommendation.HIRE, 85),
        _opinion("b", Recommendation.NO_HIRE, 80),
    ]
    conflicts = detect_conflicts(opinions)
    assert len(conflicts) == 1
    assert conflicts[0].resolution_strategy
    assert conflicts[0].root_cause


def test_no_conflicts_when_aligned():
    opinions = [_opinion(f"m{i}", Recommendation.HIRE, 85) for i in range(4)]
    assert detect_conflicts(opinions) == []


# ---------------------------------------------------------------------------
# Discussion (Module 3)
# ---------------------------------------------------------------------------


def test_discussion_identifies_agreement_and_disagreement():
    opinions = [
        _opinion("a", Recommendation.HIRE, 85),
        _opinion("b", Recommendation.HIRE, 80),
        _opinion("c", Recommendation.NO_HIRE, 85),
    ]
    disc = run_discussion(opinions)
    assert disc.agreements
    assert disc.disagreements


# ---------------------------------------------------------------------------
# Members (Modules 1, 2) — abstain when evidence is missing
# ---------------------------------------------------------------------------


def test_member_abstains_without_required_evidence():
    cand = make_candidate()
    bundle = EvidenceBundle(candidate=cand, candidate_id=cand.candidate_id)  # all evidence None
    panel = {m.role: m for m in build_panel()}
    opinion = panel["resume_expert"].review(bundle, CommitteeMode.BALANCED)
    assert opinion.abstained is True
    assert opinion.confidence <= 30


# ---------------------------------------------------------------------------
# Engine lifecycle (Modules 6, 9)
# ---------------------------------------------------------------------------


def test_engine_runs_full_committee():
    report = _engine().run(candidate=make_candidate(candidate_id="CAND_1"), jd=JD)
    assert len(report.opinions) == 7
    assert report.consensus.recommendation in list(Recommendation)
    assert report.decision.executive_summary
    assert report.decision.recommendation == report.consensus.recommendation.value
    assert 0 <= report.confidence.overall <= 100
    # Every opinion cites at least one evidence source (safety, Module 16).
    for opinion in report.opinions:
        assert opinion.evidence_sources or opinion.abstained


def test_engine_confidence_metrics_explained():
    report = _engine().run(candidate=make_candidate(), jd=JD)
    conf = report.confidence
    for value in (conf.evidence_coverage, conf.consensus_strength, conf.overall, conf.unknown_risk):
        assert 0 <= value <= 100
    # Each metric has an explanation (Module 13).
    for key in ("evidence_coverage", "consensus_strength", "decision_stability", "unknown_risk"):
        assert conf.explanations.get(key)


def test_engine_is_deterministic():
    engine = _engine()
    cand = make_candidate(candidate_id="CAND_DET")
    r1 = engine.run(candidate=cand, jd=JD)
    r2 = engine.run(candidate=cand, jd=JD)
    assert r1.consensus.recommendation == r2.consensus.recommendation
    assert abs(r1.consensus.weighted_stance - r2.consensus.weighted_stance) < 1e-9


def test_scenario_modes_are_deterministic_and_ordered():
    engine = _engine()
    cand = make_candidate(candidate_id="CAND_MODE")
    cons = engine.run(candidate=cand, jd=JD, mode=CommitteeMode.CONSERVATIVE)
    opt = engine.run(candidate=cand, jd=JD, mode=CommitteeMode.OPTIMISTIC)
    # Conservative never reads more positively than optimistic.
    assert cons.consensus.weighted_stance <= opt.consensus.weighted_stance


def test_engine_warns_without_jd():
    report = _engine().run(candidate=make_candidate(), jd="")
    assert any("No JD" in w for w in report.warnings)
    assert report.jd_summary  # still populated (a message)


# ---------------------------------------------------------------------------
# Memory (Module 7)
# ---------------------------------------------------------------------------


def test_memory_stores_and_recalls_meeting():
    engine = _engine()
    report = engine.run(candidate=make_candidate(candidate_id="CAND_MEM"), jd=JD)
    recalled = engine.memory.recall_meeting(report.meeting_id)
    assert recalled.get("candidate_id") == "CAND_MEM"
    assert engine.memory.history()
    assert engine.memory.latest_for("CAND_MEM").get("meeting_id") == report.meeting_id


# ---------------------------------------------------------------------------
# Copilot integration (Module 11)
# ---------------------------------------------------------------------------


def test_copilot_routes_committee_questions():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Run the hiring committee",
        "What did the committee disagree on?",
        "Why was this candidate rejected?",
        "What evidence supports hiring?",
        "What concerns remain?",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.HIRING_COMMITTEE


def test_copilot_committee_intent_selects_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.HIRING_COMMITTEE) == ["hiring_committee"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Analyze this candidate in detail": Intent.ANALYZE_CANDIDATE,
        "Find machine learning engineers": Intent.SEARCH_CANDIDATE,
        "Review this resume": Intent.RESUME_REVIEW,
        "Analyze this JD": Intent.JD_ANALYSIS,
        "Should we hire this candidate?": Intent.RECOMMENDATION_QUESTION,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_committee_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Run the hiring committee for CAND_0000001", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.HIRING_COMMITTEE
    assert "hiring_committee" in [t["name"] for t in turn.tools_used]
    assert "AI Hiring Committee" in turn.evidence_sources
    assert turn.answer
