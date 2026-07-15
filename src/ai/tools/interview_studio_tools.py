"""Interview Studio tool for the Recruiter Copilot (Module 13).

Exposes the :class:`InterviewStudioEngine` to the copilot as a standard
:class:`BaseTool`. Selected by intent, so the copilot *automatically* builds the
right interview package for requests like "generate interview", "create backend
interview", "interview this ML Engineer", "what questions validate the committee
concerns?" or "generate interviewer packet". The package consumes only existing
structured outputs and reuses the AI Platform, committee and orchestration
frameworks (Module 15).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.ai.core.runner import AgentRunner
from src.ai.tools.base import (
    BaseTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
    ToolValidationError,
)

# Importing the engine auto-registers the agent (AI platform + orchestration).
from src.ai.agents.interview_studio.report import InterviewStudioEngine
from src.ai.agents.interview_studio.templates import DEPTH_PROFILES, ROLE_PROFILES, detect_role

_runner: Optional[AgentRunner] = None


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner`."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


# Keyword -> depth routing, so free-text copilot requests pick the right loop length.
_DEPTH_KEYWORDS = {
    "screen": "screen",
    "phone screen": "screen",
    "quick": "screen",
    "full loop": "deep",
    "full interview": "deep",
    "deep": "deep",
    "leadership loop": "deep",
    "onsite": "deep",
}


def route_request(message: str) -> Dict[str, str]:
    """Infer the role path + interview depth from a free-text copilot message.

    Role detection reuses the deterministic role router; depth is keyword-driven
    and defaults to empty (the engine then auto-chooses from seniority).
    """
    text = (message or "").lower()
    depth = next((d for phrase, d in _DEPTH_KEYWORDS.items() if phrase in text), "")
    # Only force a role when the recruiter explicitly named one; otherwise let the
    # engine infer it from the candidate's title + JD so it stays personalized.
    role = ""
    matched = detect_role(text)
    for profile in ROLE_PROFILES.values():
        if profile.key == "generalist":
            continue
        if any(alias in text for alias in profile.aliases):
            role = matched.key
            break
    return {"role": role, "depth": depth}


class InterviewStudioTool(BaseTool):
    """Generate a complete, personalized interview package for a candidate."""

    metadata = ToolMetadata(
        name="interview_studio",
        description=(
            "Generate a complete, personalized interview package that synthesizes "
            "the committee decision, resume/JD intelligence, candidate "
            "intelligence, timeline, risk and recommendation into an interview "
            "strategy, an adaptive question flow (technical, behavioral, "
            "role-specific), risk-validation questions, evaluation rubrics, a "
            "decision matrix, feedback templates and interviewer guides — with "
            "backend/frontend/ML/DevOps/security/PM/EM role paths."
        ),
        input_fields=["candidate_id", "role", "depth"],
        engine="Interview Studio",
    )

    def validate(self, tool_input: Dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("interview_studio requires 'candidate_id'.")

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, build the interview package, and summarize it."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        routed = route_request(str(tool_input.get("message", "")))
        role = tool_input.get("role") or routed["role"]
        depth = tool_input.get("depth") or routed["depth"]

        engine = InterviewStudioEngine(
            insights_fn=context.insights_fn, ai_runner=_get_runner()
        )
        report = engine.build(candidate=candidate, jd=context.jd, role=role, depth=depth)

        narrative = report.narrative
        output = {
            "candidate_id": candidate_id,
            "role": report.role,
            "role_name": report.role_name,
            "depth": report.depth,
            "readiness": narrative.readiness_label,
            "interview_summary": narrative.interview_summary,
            "strategy_summary": report.strategy.summary,
            "length_minutes": report.strategy.length_minutes,
            "stage_count": report.strategy.stage_count,
            "roadmap": [s.name for s in report.roadmap],
            "key_probes": list(narrative.key_probes),
            "watch_areas": list(narrative.watch_areas),
            "technical_questions": [q.text for q in report.technical_questions[:5]],
            "behavioral_questions": [q.text for q in report.behavioral_questions[:5]],
            "role_specific_questions": [q.text for q in report.role_specific_questions[:5]],
            "risk_validations": [
                {"risk": rv.risk, "question": rv.validation_question, "pass_criteria": rv.pass_criteria}
                for rv in report.risk_validations[:5]
            ],
            "rubric_dimensions": [d.name for d in report.rubrics],
            "decision_bands": [b.label for b in report.decision_matrix.bands],
            "committee_alignment": report.decision_matrix.committee_alignment,
            "question_count": len(report.all_questions()),
            "available_roles": [r.key for r in ROLE_PROFILES.values()],
            "available_depths": list(DEPTH_PROFILES),
            "plan_id": report.plan_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Interview Studio built a {report.depth} {report.role_name} loop for "
                f"{candidate_id}: {report.strategy.stage_count} stages, "
                f"{len(report.all_questions())} questions, {len(report.risk_validations)} "
                f"risk validations, {len(report.rubrics)} rubric dimensions "
                f"(readiness {narrative.readiness_label})."
            ),
            evidence_sources=["Interview Studio"] + report.evidence_sources,
        )
