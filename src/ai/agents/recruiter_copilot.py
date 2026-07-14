"""RecruiterCopilotAgent — narrates structured tool outputs into recruiter prose.

This is the AI-Platform agent behind the Recruiter Copilot. It receives ONLY the
structured outputs of deterministic tools (never raw resumes or raw JSON dumps)
and produces a :class:`CopilotResponse`. Offline it uses a deterministic composer
(no hallucination, cannot contradict the engines); with a real provider it uses
the same evidence embedded in the prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.providers.composers import register_composer
from src.ai.schemas.copilot_response import CopilotResponse

# Map tool name -> the engine label to cite as evidence.
_TOOL_EVIDENCE = {
    "faiss_search": "FAISS semantic search",
    "candidate_search": "Candidate search",
    "skill_gap": "Skill-gap analyzer",
    "candidate_intelligence": "Candidate Intelligence engine",
    "timeline": "Career Timeline Intelligence",
    "risk": "Resume Risk Detection",
    "recommendation": "Hiring Recommendation engine",
    "interview": "Interview Intelligence",
    "explainability": "Rule-based explainability",
    "comparison": "Candidate Comparison engine",
    "pipeline": "Hiring Pipeline",
    "dashboard": "Recruiter Dashboard analytics",
}


@dataclass
class RecruiterCopilotInput:
    """Typed input for the RecruiterCopilotAgent.

    Attributes:
        intent: The detected intent value (string).
        message: The recruiter's message.
        tool_outputs: ``{tool_name: output_dict}`` for the tools that ran.
    """

    intent: str
    message: str
    tool_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)


def build_evidence(payload: RecruiterCopilotInput) -> Dict[str, Any]:
    """Return the structured evidence for the agent/composer."""
    return {
        "intent": payload.intent,
        "message": payload.message,
        "tools": payload.tool_outputs,
    }


# ---------------------------------------------------------------------------
# Deterministic composer (offline reasoning)
# ---------------------------------------------------------------------------


def _summarize_search(output: Dict[str, Any]) -> str:
    rows = output.get("results", [])
    if not rows:
        return "No candidates matched the query."
    lines = [
        f"{i}. {r.get('title', 'Candidate')} @ {r.get('company', '?')} "
        f"({r.get('candidate_id')}) — {r.get('years_of_experience', '?')} yrs"
        for i, r in enumerate(rows[:5], start=1)
    ]
    return "Top matches:\n" + "\n".join(lines)


def _summarize_intelligence(output: Dict[str, Any]) -> str:
    return (
        f"Intelligence: overall {output.get('overall', 0):.0f}/100, technical "
        f"{output.get('technical', 0):.0f}, leadership {output.get('leadership', 0):.0f}, "
        f"engine recommendation '{output.get('recommendation', 'n/a')}'."
    )


def _summarize_timeline(output: Dict[str, Any]) -> str:
    return (
        f"Career: {output.get('summary', 'trajectory analysed')} "
        f"(timeline {output.get('timeline_score', 0):.0f}/100, "
        f"{output.get('promotion_count', 0)} promotion(s))."
    )


def _summarize_risk(output: Dict[str, Any]) -> str:
    flags = output.get("red_flags", [])
    tail = f" Red flags: {', '.join(flags)}." if flags else " No red flags."
    return (
        f"Risk: {output.get('risk_level', 'Unknown')} "
        f"(score {output.get('risk_score', 0):.0f}/100).{tail}"
    )


def _summarize_recommendation(output: Dict[str, Any]) -> str:
    reasons = output.get("reasons", [])
    tail = f" Reasons: {'; '.join(reasons)}." if reasons else ""
    return (
        f"Recommendation: {output.get('recommendation', 'n/a')} "
        f"({output.get('confidence', 0):.0f}% confidence).{tail}"
    )


def _summarize_interview(output: Dict[str, Any]) -> str:
    topics = output.get("technical_topics", []) + output.get("system_design_topics", [])
    return "Interview focus: " + ("; ".join(topics[:5]) if topics else "standard rounds") + "."


def _summarize_skill_gap(output: Dict[str, Any]) -> str:
    missing = output.get("missing", [])
    tail = f" Missing: {', '.join(missing)}." if missing else " No JD skill gaps."
    return f"Skill match: {output.get('match_percent', 0)}%.{tail}"


def _summarize_comparison(output: Dict[str, Any]) -> str:
    rows = output.get("rows", [])
    best = output.get("best_by_metric", {})
    if not rows:
        return "No comparison data."
    leader = best.get("overall_score")
    lines = [
        f"- {r.get('title')} ({r.get('candidate_id')}): overall "
        f"{r.get('overall_score', 0):.0f}, technical {r.get('technical_score', 0):.0f}, "
        f"risk {r.get('risk_level')}"
        for r in rows
    ]
    tail = f" Strongest overall: {leader}." if leader else ""
    return "Comparison:\n" + "\n".join(lines) + tail


def _summarize_pipeline(output: Dict[str, Any]) -> str:
    if output.get("tracked") is False:
        return "Pipeline: candidate is not yet tracked."
    if "current_stage" in output:
        return (
            f"Pipeline: at '{output.get('current_stage')}' "
            f"({output.get('status')}), priority {output.get('priority')}."
        )
    dist = output.get("stage_distribution", {})
    active = {k: v for k, v in dist.items() if v}
    return f"Pipeline distribution: {active or 'no candidates tracked'}."


def _summarize_dashboard(output: Dict[str, Any]) -> str:
    skills = output.get("top_skills", [])[:5]
    skill_str = ", ".join(f"{s}({c})" for s, c in skills) if skills else "n/a"
    return (
        f"Cohort: {output.get('candidate_count', 0)} candidates, avg experience "
        f"{output.get('average_experience', 0)} yrs. Top skills: {skill_str}."
    )


def _summarize_explainability(output: Dict[str, Any]) -> str:
    reasons = output.get("reasons", [])
    tail = f" Reasons: {'; '.join(reasons)}." if reasons else ""
    return f"Rule-based ranking total {output.get('total_score', 'n/a')}.{tail}"


_SUMMARIZERS = {
    "faiss_search": _summarize_search,
    "candidate_search": _summarize_search,
    "candidate_intelligence": _summarize_intelligence,
    "timeline": _summarize_timeline,
    "risk": _summarize_risk,
    "recommendation": _summarize_recommendation,
    "interview": _summarize_interview,
    "skill_gap": _summarize_skill_gap,
    "comparison": _summarize_comparison,
    "pipeline": _summarize_pipeline,
    "dashboard": _summarize_dashboard,
    "explainability": _summarize_explainability,
}

_INTENT_LEAD = {
    "Search Candidate": "Here are the candidates that best match your search.",
    "Skill Search": "Here are the candidates matching the requested skills.",
    "Compare Candidates": "Here is how the candidates compare on the deterministic metrics.",
    "Explain Ranking": "Here is why this candidate ranks where they do.",
    "Generate Hiring Summary": "Here is the hiring summary based on the intelligence engines.",
    "Analyze Candidate": "Here is a structured analysis of the candidate.",
    "Generate Interview Plan": "Here is a structured interview plan.",
    "Pipeline Question": "Here is the pipeline status.",
    "Dashboard Question": "Here is the cohort overview.",
    "Recommendation Question": "Here is the hiring recommendation and its basis.",
    "General Hiring Question": "Here is guidance based on recruiting best practice.",
}


def compose_copilot_response(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically compose a :class:`CopilotResponse` from tool outputs."""
    intent = evidence.get("intent", "")
    tools: Dict[str, Any] = evidence.get("tools", {}) or {}

    lead = _INTENT_LEAD.get(intent, "Here is what the deterministic engines report.")
    sections: List[str] = []
    evidence_sources: List[str] = []

    for name, output in tools.items():
        summarizer = _SUMMARIZERS.get(name)
        if summarizer is None or not isinstance(output, dict):
            continue
        if output.get("error"):
            continue
        sections.append(summarizer(output))
        if name in _TOOL_EVIDENCE:
            evidence_sources.append(_TOOL_EVIDENCE[name])

    if sections:
        answer = lead + "\n\n" + "\n\n".join(sections)
    else:
        answer = (
            f"{lead} I don't have specific tool evidence for this request yet — "
            "please name a candidate or provide a search query so I can pull the "
            "relevant deterministic intelligence."
        )

    reasoning_summary = (
        f"Derived from {len(sections)} tool output(s): "
        f"{', '.join(dict.fromkeys(evidence_sources)) or 'none'}."
    )

    # Confidence / uncertainty.
    risk = tools.get("risk", {})
    intel = tools.get("candidate_intelligence", {})
    low_confidence = (
        (isinstance(intel, dict) and intel.get("confidence", 100) < 55)
        or (isinstance(risk, dict) and risk.get("risk_level") == "High")
        or not sections
    )
    confidence_note = (
        "Confidence is limited — evidence is thin or risk is elevated; validate "
        "before acting."
        if low_confidence
        else "Confidence is solid — the engine signals are consistent."
    )

    return {
        "answer": answer,
        "reasoning_summary": reasoning_summary,
        "evidence_sources": list(dict.fromkeys(evidence_sources)),
        "confidence_note": confidence_note,
    }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class RecruiterCopilotAgent(BaseAgent):
    """Turns structured tool outputs into a recruiter-quality answer."""

    metadata = AgentMetadata(
        name="recruiter_copilot",
        version="v1",
        title="Recruiter Copilot",
        description=(
            "Narrates the deterministic engines' tool outputs into professional, "
            "evidence-based recruiter answers. Never scores or fabricates."
        ),
        prompt_id="recruiter_copilot",
        prompt_version="v1",
        tags=["copilot", "recruiter", "reasoning"],
    )
    output_schema = CopilotResponse

    def build_evidence(self, payload: RecruiterCopilotInput) -> Dict[str, Any]:
        """Return the structured evidence (intent + message + tool outputs)."""
        return build_evidence(payload)

    def prompt_values(
        self, payload: RecruiterCopilotInput, evidence: Dict[str, Any]
    ) -> Dict[str, str]:
        """Supply the recruiter message + intent placeholders."""
        return {"recruiter_message": payload.message, "intent": payload.intent}

    def cache_dimensions(self, payload: RecruiterCopilotInput) -> Tuple[str, str]:
        """Cache by intent (subject) and message + tool-output signature (scope)."""
        signature = json.dumps(payload.tool_outputs, sort_keys=True, default=str)
        return payload.intent or "general", f"{payload.message}||{signature}"


register_composer(CopilotResponse.schema_name(), compose_copilot_response)
recruiter_copilot_agent = registry.register(RecruiterCopilotAgent())
