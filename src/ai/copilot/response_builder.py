"""Response builder — assembles the final :class:`CopilotTurn`.

Combines the AI narration (from the platform) with **deterministic** follow-up
suggestions (Module 7) and recruiter actions (Module 10), plus tool-visibility
metadata (Module 9). Keeping follow-ups/actions deterministic makes them fast,
predictable and testable.
"""

from __future__ import annotations

from typing import List, Optional

from src.ai.core.response import AgentResult, AgentStatus
from src.ai.tools.base import ToolResult
from src.ai.copilot.models import (
    CopilotAction,
    CopilotPlan,
    CopilotTurn,
    Intent,
    IntentResult,
)

# Deterministic follow-up questions per intent (3 each).
_FOLLOW_UPS = {
    Intent.SEARCH_CANDIDATE: [
        "Would you like to compare the top candidates?",
        "Should I analyze the top match in detail?",
        "Want me to generate a hiring summary for one of them?",
    ],
    Intent.SKILL_SEARCH: [
        "Should I show the skill gaps for the top match?",
        "Would you like to compare these candidates?",
        "Want an interview plan focused on these skills?",
    ],
    Intent.COMPARE_CANDIDATES: [
        "Should I generate a hiring summary for the strongest candidate?",
        "Want the risk report for these candidates?",
        "Shall I create interview plans for them?",
    ],
    Intent.EXPLAIN_RANKING: [
        "Would you like the full hiring recommendation?",
        "Should I show the risk assessment?",
        "Want to compare this candidate with another?",
    ],
    Intent.GENERATE_HIRING_SUMMARY: [
        "Should I generate an interview plan?",
        "Want the risk report and validation questions?",
        "Shall I move this candidate to the shortlist?",
    ],
    Intent.ANALYZE_CANDIDATE: [
        "Should I generate an interview plan for this candidate?",
        "Want to move them to the shortlist?",
        "Shall I compare them with another candidate?",
    ],
    Intent.GENERATE_INTERVIEW_PLAN: [
        "Should I move this candidate to the interview stage?",
        "Want the risk-based validation questions?",
        "Shall I generate a hiring summary too?",
    ],
    Intent.PIPELINE_QUESTION: [
        "Should I move a candidate to the next stage?",
        "Want the overall pipeline funnel?",
        "Shall I show the shortlisted candidates?",
    ],
    Intent.DASHBOARD_QUESTION: [
        "Want the risk distribution across candidates?",
        "Should I surface the top candidates for a role?",
        "Shall I break this down by location?",
    ],
    Intent.RECOMMENDATION_QUESTION: [
        "Should I generate the full hiring summary?",
        "Want the interview plan for this candidate?",
        "Shall I move them to the shortlist?",
    ],
    Intent.RESUME_REVIEW: [
        "Want the prioritized improvement plan?",
        "Should I check ATS keyword coverage against a JD?",
        "Shall I highlight the biggest resume weaknesses?",
    ],
    Intent.JD_ANALYSIS: [
        "Want the prioritized JD improvement plan?",
        "Should I explain the inferred hiring intent?",
        "Shall I separate the mandatory vs preferred requirements?",
    ],
    Intent.HIRING_COMMITTEE: [
        "What did the committee disagree on?",
        "What are the remaining unknowns?",
        "What evidence supports the recommendation?",
    ],
    Intent.INTERVIEW_STUDIO: [
        "What questions validate the committee's concerns?",
        "Generate a backend/ML interviewer packet for this candidate.",
        "Show the evaluation rubric and decision matrix.",
    ],
    Intent.COMPENSATION_GOVERNANCE: [
        "Show the full offer justification and audit trail.",
        "What is the negotiation strategy?",
        "Create the finance approval report.",
    ],
    Intent.PAY_EQUITY: [
        "Show the compression and inversion analysis.",
        "Who should approve this offer?",
        "Does this violate our pay policy?",
    ],
    Intent.HIRING_COMPLIANCE: [
        "What approvals are missing?",
        "What documentation is missing?",
        "Show the audit trail and governance risk.",
    ],
    Intent.HIRING_AUDIT: [
        "Show the decision timeline.",
        "Which agents and evidence influenced this decision?",
        "Show the approval history and audit readiness.",
    ],
    Intent.HIRING_INTELLIGENCE: [
        "What are our hiring bottlenecks?",
        "Which departments need improvement?",
        "Generate the executive workforce report.",
    ],
    Intent.GENERAL_HIRING_QUESTION: [
        "Would you like to search for candidates?",
        "Should I analyze a specific candidate?",
        "Want an overview of the candidate pool?",
    ],
}


def suggest_follow_ups(intent: Intent) -> List[str]:
    """Return 3 deterministic follow-up questions for ``intent``."""
    return list(_FOLLOW_UPS.get(intent, _FOLLOW_UPS[Intent.GENERAL_HIRING_QUESTION]))


def suggest_actions(plan: CopilotPlan) -> List[CopilotAction]:
    """Return recruiter actions relevant to the plan's intent + resolved refs."""
    actions: List[CopilotAction] = []
    candidate = plan.focus_candidate
    comparison = plan.comparison_ids

    def candidate_actions(cid: str) -> List[CopilotAction]:
        return [
            CopilotAction("move_to_shortlist", "⭐ Move to Shortlist", {"candidate_id": cid}),
            CopilotAction("generate_interview_plan", "🗓 Interview Plan", {"candidate_id": cid}),
            CopilotAction("open_profile", "👤 Open Profile", {"candidate_id": cid}),
            CopilotAction("view_risk", "🚨 View Risk", {"candidate_id": cid}),
            CopilotAction("view_timeline", "📈 View Timeline", {"candidate_id": cid}),
            CopilotAction("generate_hiring_report", "📄 Hiring Report", {"candidate_id": cid}),
        ]

    single_intents = {
        Intent.ANALYZE_CANDIDATE,
        Intent.GENERATE_HIRING_SUMMARY,
        Intent.RECOMMENDATION_QUESTION,
        Intent.EXPLAIN_RANKING,
        Intent.GENERATE_INTERVIEW_PLAN,
        Intent.HIRING_COMMITTEE,
        Intent.RESUME_REVIEW,
        Intent.INTERVIEW_STUDIO,
        Intent.COMPENSATION_GOVERNANCE,
        Intent.PAY_EQUITY,
        Intent.HIRING_COMPLIANCE,
        Intent.HIRING_AUDIT,
    }

    if plan.intent in single_intents and candidate:
        actions = candidate_actions(candidate)
    elif plan.intent == Intent.COMPARE_CANDIDATES and len(comparison) >= 2:
        actions = [
            CopilotAction("compare_candidates", "🆚 Open Comparison", {"candidate_ids": comparison}),
            CopilotAction("generate_hiring_report", "📄 Hiring Report", {"candidate_id": comparison[0]}),
        ]
    elif plan.intent in {Intent.SEARCH_CANDIDATE, Intent.SKILL_SEARCH} and candidate:
        actions = [
            CopilotAction("analyze_candidate", "🔍 Analyze Top Match", {"candidate_id": candidate}),
            CopilotAction("move_to_shortlist", "⭐ Shortlist Top Match", {"candidate_id": candidate}),
        ]
        if len(comparison) >= 2:
            actions.append(
                CopilotAction("compare_candidates", "🆚 Compare Top Two", {"candidate_ids": comparison})
            )
    elif plan.intent == Intent.PIPELINE_QUESTION and candidate:
        actions = [
            CopilotAction("move_to_shortlist", "⭐ Move to Shortlist", {"candidate_id": candidate}),
        ]

    return actions


def build_turn(
    message: str,
    intent_result: IntentResult,
    plan: CopilotPlan,
    tool_results: List[ToolResult],
    ai_result: AgentResult,
    latency_ms: float,
) -> CopilotTurn:
    """Assemble the final :class:`CopilotTurn` from all pieces."""
    data = ai_result.data
    answer = getattr(data, "answer", "") if data else ""
    reasoning = getattr(data, "reasoning_summary", "") if data else ""
    confidence_note = getattr(data, "confidence_note", "") if data else ""

    # Evidence sources: prefer the AI's cited set, else union the tools'.
    evidence_sources = list(getattr(data, "evidence_sources", []) or [])
    if not evidence_sources:
        for result in tool_results:
            evidence_sources.extend(result.evidence_sources)
    evidence_sources = list(dict.fromkeys(evidence_sources))

    status = "ok" if (ai_result.ok and answer) else "failed"
    error = None if status == "ok" else (ai_result.error or "No answer produced.")
    if status == "failed" and not answer:
        answer = (
            "I couldn't produce an answer for that request. Please rephrase or "
            "specify a candidate."
        )

    return CopilotTurn(
        message=message,
        answer=answer,
        intent=intent_result.intent,
        reasoning_summary=reasoning,
        confidence_note=confidence_note,
        tools_used=[r.to_summary_dict() for r in tool_results],
        evidence_sources=evidence_sources,
        follow_ups=suggest_follow_ups(intent_result.intent),
        actions=suggest_actions(plan),
        provider=ai_result.provider,
        model=ai_result.model,
        cache_hit=ai_result.cache_hit,
        latency_ms=latency_ms,
        status=status,
        error=error,
    )
