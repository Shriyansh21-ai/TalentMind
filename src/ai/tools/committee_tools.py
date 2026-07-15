"""AI Hiring Committee tool for the Recruiter Copilot (Module 11).

Exposes the :class:`HiringCommitteeEngine` to the copilot as a standard
:class:`BaseTool`. Selected by intent, so the copilot *automatically* convenes
the committee for questions like "run the hiring committee", "what did they
disagree on?", "why was this candidate rejected?". The committee consumes only
cached structured outputs and reuses the AI Platform + orchestration framework.
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

# Importing the engine auto-registers the chair (AI platform) + the committee
# (orchestration registry).
from src.ai.committee.committee import HiringCommitteeEngine
from src.ai.committee.schemas import CommitteeMode

_runner: Optional[AgentRunner] = None


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner`."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


class HiringCommitteeTool(BaseTool):
    """Convene the AI Hiring Committee for a candidate and package the report."""

    metadata = ToolMetadata(
        name="hiring_committee",
        description=(
            "Convene a panel of AI specialists that independently review the "
            "existing engine outputs, debate, resolve conflicts and produce one "
            "evidence-backed executive hiring decision."
        ),
        input_fields=["candidate_id", "mode"],
        engine="AI Hiring Committee",
    )

    def validate(self, tool_input: Dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("hiring_committee requires 'candidate_id'.")

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, run the committee, and summarize the report."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        mode = tool_input.get("mode", CommitteeMode.BALANCED)
        engine = HiringCommitteeEngine(
            insights_fn=context.insights_fn, ai_runner=_get_runner()
        )
        report = engine.run(candidate=candidate, jd=context.jd, mode=mode)

        decision = report.decision
        output = {
            "candidate_id": candidate_id,
            "recommendation": report.consensus.recommendation.value,
            "consensus_level": report.consensus.level.value,
            "consensus_reasoning": report.consensus.reasoning,
            "overall_confidence": report.confidence.overall,
            "opinions": [
                {
                    "role": o.role_title,
                    "recommendation": o.recommendation.value,
                    "confidence": o.confidence,
                    "top_evidence": o.evidence[0] if o.evidence else "",
                }
                for o in report.opinions
            ],
            "agreements": list(report.discussion.agreements),
            "disagreements": list(report.discussion.disagreements),
            "conflicts": [
                {"between": f"{c.member_a} vs {c.member_b}", "resolution": c.resolution_strategy}
                for c in report.conflicts[:4]
            ],
            "executive_summary": decision.executive_summary,
            "business_justification": decision.business_justification,
            "technical_justification": decision.technical_justification,
            "hiring_risks": list(decision.hiring_risks),
            "interview_priorities": list(decision.interview_priorities),
            "remaining_unknowns": list(decision.remaining_unknowns),
            "follow_up_actions": list(decision.follow_up_actions),
            "confidence_explanations": report.confidence.explanations,
            "meeting_id": report.meeting_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Committee reached {report.consensus.level.value} and recommends "
                f"{report.consensus.recommendation.value} "
                f"(confidence {report.confidence.overall:.0f}/100, "
                f"{len(report.conflicts)} conflict(s))."
            ),
            evidence_sources=["AI Hiring Committee"] + report.evidence_sources,
            confidence=report.confidence.overall,
        )
