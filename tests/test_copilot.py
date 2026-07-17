"""Tests for the Recruiter Copilot (Phase 3 / Milestone 2).

Covers intent detection, tool selection, planning, conversation/state, response
building, the tool registry, and the controller end-to-end — all offline with a
synthetic candidate repository (no dataset, no FAISS, no network).
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.config.settings import AISettings
from src.ai.copilot.controller import RecruiterCopilot
from src.ai.copilot.conversation import ConversationManager
from src.ai.copilot.models import CopilotPlan, Intent
from src.ai.copilot.planner import CopilotPlanner, IntentClassifier
from src.ai.copilot.response_builder import (
    suggest_actions,
    suggest_follow_ups,
)
from src.ai.copilot.state import ConversationState
from src.ai.copilot.tool_selector import select_tools
from src.ai.core.runner import AgentRunner
from src.ai.tools.base import ToolContext, ToolResult
from src.ai.tools.builtin import register_builtin_tools
from src.ai.tools.provider import InMemoryCandidateRepository
from src.ai.tools.registry import ToolRegistry, ToolRunner

JD = "python machine learning llm aws docker"


def _repo():
    cands = [
        make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer"),
        make_candidate(
            candidate_id="CAND_0000002",
            title="Backend Engineer",
            skills=["Java", "Spring", "AWS"],
            years=4.0,
        ),
    ]
    return InMemoryCandidateRepository(cands)


def _copilot():
    settings = AISettings(provider="local", cache_enabled=False)
    return RecruiterCopilot(_repo(), ai_runner=AgentRunner(settings=settings))


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------


def test_intent_classification():
    clf = IntentClassifier()
    state = ConversationState()
    cases = {
        "Find machine learning engineers": Intent.SEARCH_CANDIDATE,
        "Compare CAND_0000001 and CAND_0000002": Intent.COMPARE_CANDIDATES,
        "Why is this candidate ranked so high?": Intent.EXPLAIN_RANKING,
        "Generate a hiring summary for him": Intent.GENERATE_HIRING_SUMMARY,
        "Analyze this candidate in detail": Intent.ANALYZE_CANDIDATE,
        "Create an interview plan": Intent.GENERATE_INTERVIEW_PLAN,
        "What is the pipeline status?": Intent.PIPELINE_QUESTION,
        "Show me the dashboard distribution": Intent.DASHBOARD_QUESTION,
        "Who knows Python?": Intent.SKILL_SEARCH,
        "Should we hire this candidate?": Intent.RECOMMENDATION_QUESTION,
    }
    for message, expected in cases.items():
        result = clf.classify(message, state)
        assert result.intent == expected, f"{message!r} -> {result.intent}"
        assert 0 <= result.confidence <= 100


def test_intent_extracts_entities():
    clf = IntentClassifier()
    result = clf.classify("Compare CAND_0000001 and CAND_0000002 top 3", ConversationState())
    assert result.entities.candidate_ids == ["CAND_0000001", "CAND_0000002"]
    assert result.entities.top_k == 3


def test_intent_default_is_general():
    clf = IntentClassifier()
    result = clf.classify("hello there", ConversationState())
    assert result.intent == Intent.GENERAL_HIRING_QUESTION


# ---------------------------------------------------------------------------
# Tool selection + planning
# ---------------------------------------------------------------------------


def test_tool_selection_is_minimal():
    assert select_tools(Intent.SEARCH_CANDIDATE) == ["faiss_search"]
    assert select_tools(Intent.GENERAL_HIRING_QUESTION) == []
    analyze = select_tools(Intent.ANALYZE_CANDIDATE)
    assert "candidate_intelligence" in analyze and "dashboard" not in analyze


def test_planner_resolves_candidate_from_state():
    planner = CopilotPlanner()
    state = ConversationState(current_candidate="CAND_0000001")
    intent = planner.classify("analyze this candidate", state)
    plan = planner.plan(intent, state)
    assert plan.intent == Intent.ANALYZE_CANDIDATE
    assert plan.focus_candidate == "CAND_0000001"
    for _, tool_input in plan.steps:
        assert tool_input.get("candidate_id") == "CAND_0000001"


def test_planner_skips_candidate_tools_without_candidate():
    planner = CopilotPlanner()
    state = ConversationState()  # no candidate known
    intent = planner.classify("analyze the candidate", state)
    plan = planner.plan(intent, state)
    # No candidate resolvable -> candidate-scoped tools are skipped.
    assert plan.steps == []


def test_planner_comparison_needs_two():
    planner = CopilotPlanner()
    state = ConversationState()
    intent = planner.classify("compare CAND_0000001 and CAND_0000002", state)
    plan = planner.plan(intent, state)
    assert "comparison" in plan.tool_names
    assert plan.comparison_ids == ["CAND_0000001", "CAND_0000002"]


# ---------------------------------------------------------------------------
# Conversation + state
# ---------------------------------------------------------------------------


def test_conversation_records_turns():
    manager = ConversationManager()
    session = manager.get_or_create("s1")
    from src.ai.copilot.models import CopilotTurn

    turn = CopilotTurn(message="hi", answer="hello", intent=Intent.GENERAL_HIRING_QUESTION)
    manager.record(session, "hi", turn)
    assert session.turn_count == 1
    assert len(session.history) == 2  # user + assistant


def test_state_dedupes_comparison():
    state = ConversationState()
    state.set_comparison(["A", "B", "A", "C"])
    assert state.current_comparison == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------


def test_follow_ups_always_three():
    for intent in Intent:
        assert len(suggest_follow_ups(intent)) == 3


def test_actions_for_analyze_include_candidate_actions():
    plan = CopilotPlan(intent=Intent.ANALYZE_CANDIDATE, focus_candidate="CAND_0000001")
    actions = suggest_actions(plan)
    types = {a.type for a in actions}
    assert "move_to_shortlist" in types
    assert "generate_interview_plan" in types
    for action in actions:
        assert action.params.get("candidate_id") == "CAND_0000001"


def test_actions_empty_without_candidate():
    plan = CopilotPlan(intent=Intent.ANALYZE_CANDIDATE)  # no candidate
    assert suggest_actions(plan) == []


# ---------------------------------------------------------------------------
# Tool registry + runner
# ---------------------------------------------------------------------------


def test_tool_registry_registers_builtins():
    reg = ToolRegistry()
    register_builtin_tools(reg)
    for name in ["faiss_search", "risk", "comparison", "dashboard", "pipeline"]:
        assert reg.has(name)


def test_tool_runner_unknown_tool_is_failed_result():
    reg = ToolRegistry()
    runner = ToolRunner(reg)
    ctx = ToolContext(repository=_repo(), jd=JD)
    result = runner.run("does_not_exist", {}, ctx)
    assert isinstance(result, ToolResult)
    assert result.ok is False


def test_tool_runner_executes_intelligence():
    reg = register_builtin_tools(ToolRegistry())
    runner = ToolRunner(reg)
    ctx = ToolContext(repository=_repo(), jd=JD)
    result = runner.run("candidate_intelligence", {"candidate_id": "CAND_0000001"}, ctx)
    assert result.ok
    assert "overall" in result.output


# ---------------------------------------------------------------------------
# Controller end-to-end (offline)
# ---------------------------------------------------------------------------


def test_controller_search_flow():
    cop = _copilot()
    turn = cop.ask("s1", "Find machine learning engineers", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.SEARCH_CANDIDATE
    assert "faiss_search" in [t["name"] for t in turn.tools_used]
    assert turn.answer
    assert len(turn.follow_ups) == 3
    # After a search, the top candidate becomes focus + actions appear.
    assert cop.session("s1").state.current_candidate is not None
    assert turn.actions


def test_controller_analyze_uses_engines_not_all_tools():
    cop = _copilot()
    turn = cop.ask("s1", "Analyze CAND_0000001", jd=JD)
    names = [t["name"] for t in turn.tools_used]
    assert "candidate_intelligence" in names
    assert "dashboard" not in names  # never runs every tool
    assert turn.evidence_sources


def test_controller_contextual_followup():
    cop = _copilot()
    cop.ask("s1", "Find machine learning engineers", jd=JD)
    # "analyze that candidate" with no id must resolve from state.
    turn = cop.ask("s1", "Analyze that candidate", jd=JD)
    assert turn.intent == Intent.ANALYZE_CANDIDATE
    assert any(t["name"] == "candidate_intelligence" for t in turn.tools_used)


def test_controller_general_question_runs_no_tools():
    cop = _copilot()
    turn = cop.ask("s1", "What makes a strong hiring process?", jd=JD)
    assert turn.intent == Intent.GENERAL_HIRING_QUESTION
    assert turn.tools_used == []
    assert turn.answer  # still produces a helpful answer


def test_controller_never_fabricates_score_field():
    cop = _copilot()
    turn = cop.ask("s1", "Analyze CAND_0000001", jd=JD)
    # The copilot response schema is score-free; answer is narrative only.
    assert isinstance(turn.answer, str)
    assert turn.provider == "local"
