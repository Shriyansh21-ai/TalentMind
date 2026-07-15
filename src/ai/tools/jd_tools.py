"""JD-analysis tool for the Recruiter Copilot (Module 14).

Exposes the :class:`JDAnalystAgent` to the copilot as a standard
:class:`BaseTool`. Because tools are discovered by name through the tool
registry and selected by intent, adding this tool + its intent mapping is all it
takes for the copilot to *automatically* delegate JD questions to the agent — no
per-request manual routing.

The JD text comes from the conversation's current JD (``ToolContext.jd``) unless
one is passed explicitly. The tool runs the agent through the shared
:class:`AgentRunner`, reusing the provider layer, cache, telemetry and safety.
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

# Importing the agent module auto-registers the JDAnalystAgent with the AI
# platform registry, the composer registry and the orchestration registry.
from src.ai.agents.jd.agent import JDAnalystInput, jd_analyst_agent

_runner: Optional[AgentRunner] = None


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner` (offline by default)."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


class JDAnalysisTool(BaseTool):
    """Run the JDAnalystAgent for the current JD and package the result."""

    metadata = ToolMetadata(
        name="jd_analysis",
        description=(
            "Enterprise JD intelligence: role level, technical shape, hiring intent, "
            "organization context, requirement hierarchy, market posture, quality "
            "and evidence-based JD risks."
        ),
        input_fields=["jd_text"],
        engine="JD Analyst Agent",
    )

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Analyze the current JD (from input or conversation context)."""
        jd_text = (tool_input.get("jd_text") or getattr(context, "jd", "") or "").strip()
        if not jd_text:
            return ToolResult(
                name=self.metadata.name,
                ok=False,
                error=(
                    "No job description is attached to this conversation. Provide or "
                    "upload a JD so I can analyze it."
                ),
                evidence_sources=["JD Analyst Agent"],
            )

        result = _get_runner().run(
            jd_analyst_agent, JDAnalystInput(jd_text=jd_text, jd_id=str(tool_input.get("jd_id", "")))
        )
        if not result.ok or result.data is None:
            return ToolResult(
                name=self.metadata.name,
                ok=False,
                error=result.error or "JD analysis unavailable.",
                evidence_sources=["JD Analyst Agent"],
            )

        a = result.data
        q = a.quality
        output = {
            "executive_summary": a.executive_summary,
            "overall_quality": q.overall,
            "dimensions": q.to_dict(),
            "seniority": a.role_intelligence.seniority,
            "technical_level": a.role_intelligence.technical_level,
            "role_confidence": a.role_intelligence.confidence,
            "primary_intent": a.hiring_intent.primary_intent,
            "intent_confidence": a.hiring_intent.confidence,
            "company_type": a.organization_intelligence.company_type,
            "mandatory": list(a.requirement_hierarchy.mandatory),
            "preferred": list(a.requirement_hierarchy.preferred),
            "hidden_expectations": list(a.requirement_hierarchy.hidden_expectations),
            "risk_level": a.risk_report.level,
            "risk_findings": [f.to_dict() for f in a.risk_report.findings],
            "strengths": list(a.strengths),
            "weaknesses": list(a.weaknesses),
            "top_improvements": [
                {"title": i.title, "priority": i.priority, "area": i.area}
                for i in a.improvement_plan[:5]
            ],
            "confidence_note": a.confidence_note,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"JD quality {q.overall:.0f}/100; role {a.role_intelligence.seniority}; "
                f"intent {a.hiring_intent.primary_intent} ({a.hiring_intent.confidence:.0f}%); "
                f"JD risk {a.risk_report.level}."
            ),
            evidence_sources=["JD Analyst Agent"],
        )
