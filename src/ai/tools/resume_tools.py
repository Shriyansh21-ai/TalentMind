"""Resume-analysis tool for the Recruiter Copilot (Module 14).

Exposes the :class:`ResumeAnalystAgent` to the copilot as a standard
:class:`BaseTool`. Because tools are discovered by name through the tool
registry and selected by intent, adding this tool + its intent mapping is all it
takes for the copilot to *automatically* delegate resume questions to the agent —
no per-request manual routing.

The tool runs the agent through the shared :class:`AgentRunner`, so it reuses the
platform's provider layer, cache, telemetry, safety and structured output.
"""

from __future__ import annotations

from typing import Any

# Importing the agent module auto-registers the ResumeAnalystAgent with the AI
# platform registry, the composer registry and the orchestration registry, so
# simply having this tool available guarantees the agent is discoverable.
from src.ai.agents.resume.agent import ResumeAnalystInput, resume_analyst_agent
from src.ai.core.runner import AgentRunner
from src.ai.tools.base import (
    BaseTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
    ToolValidationError,
)

_runner: AgentRunner | None = None


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner` (offline by default)."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


class ResumeAnalysisTool(BaseTool):
    """Run the ResumeAnalystAgent for a candidate and package the result."""

    metadata = ToolMetadata(
        name="resume_analysis",
        description=(
            "Recruiter-grade resume intelligence: quality, writing, ATS, projects, "
            "achievements, career story and evidence-based resume risks."
        ),
        input_fields=["candidate_id"],
        engine="Resume Analyst Agent",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("resume_analysis requires 'candidate_id'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, run the agent, and summarize the analysis."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        payload = ResumeAnalystInput(candidate_id=candidate_id, candidate=candidate, jd=context.jd)
        result = _get_runner().run(resume_analyst_agent, payload)
        if not result.ok or result.data is None:
            return ToolResult(
                name=self.metadata.name,
                ok=False,
                error=result.error or "Resume analysis unavailable.",
                evidence_sources=["Resume Analyst Agent"],
            )

        analysis = result.data
        quality = analysis.resume_quality
        risk = analysis.risk_report
        output = {
            "candidate_id": candidate_id,
            "executive_summary": analysis.executive_summary,
            "overall_quality": quality.overall,
            "dimensions": quality.to_dict(),
            "strengths": list(analysis.strengths),
            "weaknesses": list(analysis.weaknesses),
            "career_direction": analysis.career_story.direction,
            "ats_friendliness": analysis.ats_report.friendliness,
            "missing_keywords": list(analysis.ats_report.missing_keywords),
            "risk_level": risk.level,
            "risk_findings": [f.to_dict() for f in risk.findings],
            "top_improvements": [
                {"title": i.title, "priority": i.priority, "area": i.area}
                for i in analysis.improvement_plan[:5]
            ],
            "confidence_note": analysis.confidence_note,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Resume quality {quality.overall:.0f}/100; ATS "
                f"{analysis.ats_report.friendliness}; resume risk {risk.level}; "
                f"{len(analysis.improvement_plan)} improvement(s)."
            ),
            evidence_sources=["Resume Analyst Agent"],
        )
