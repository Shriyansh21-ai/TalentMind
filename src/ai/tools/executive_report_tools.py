"""Executive Hiring Report tool for the Recruiter Copilot (Module 14).

Exposes the :class:`ExecutiveReportBuilder` + export engine to the copilot as a
standard :class:`BaseTool`. Selected by intent, so the copilot *automatically*
generates the right report for requests like "generate executive report",
"generate CTO report", "export committee report" or "create interview packet".
The report consumes only existing structured outputs and reuses the AI Platform,
committee and orchestration frameworks (Module 15).
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

# Importing the builder auto-registers the agent (AI platform + orchestration).
from src.ai.agents.executive_report.builder import ExecutiveReportBuilder
from src.ai.agents.executive_report.export import FORMATS, PACKETS, export_report, suffix_for
from src.ai.agents.executive_report.templates import TEMPLATES, get_template

_runner: Optional[AgentRunner] = None


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner`."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


# Keyword → template routing, so free-text copilot requests pick the right layout.
_TEMPLATE_KEYWORDS = {
    "cto": "cto",
    "ceo": "ceo",
    "chief technology": "cto",
    "chief executive": "ceo",
    "engineering manager": "engineering_manager",
    "hiring manager": "engineering_manager",
    "recruiter": "recruiter",
    "committee": "committee",
    "hr": "hr",
    "people": "hr",
}
_PACKET_KEYWORDS = {
    "interview packet": "interview_packet",
    "committee report": "committee_report",
    "candidate report": "candidate_report",
    "recruiter report": "recruiter_report",
    "hiring manager report": "hiring_manager_report",
    "executive summary": "executive_summary",
}


def route_request(message: str) -> Dict[str, str]:
    """Infer the template/packet/format from a free-text copilot message."""
    text = (message or "").lower()
    packet = next((p for phrase, p in _PACKET_KEYWORDS.items() if phrase in text), "")
    template = next((t for phrase, t in _TEMPLATE_KEYWORDS.items() if phrase in text), "")
    if packet and not template:
        template = get_template(PACKETS[packet].template).key
    fmt = ""
    for candidate in ("pdf", "docx", "html", "pptx", "powerpoint", "word"):
        if candidate in text:
            fmt = {"powerpoint": "pptx", "word": "docx"}.get(candidate, candidate)
            break
    return {"template": template or "executive", "packet": packet, "format": fmt}


class ExecutiveReportTool(BaseTool):
    """Generate an executive hiring report (and optionally an export) for a candidate."""

    metadata = ToolMetadata(
        name="executive_report",
        description=(
            "Generate a boardroom-grade executive hiring report that synthesizes "
            "the committee decision, resume/JD intelligence, candidate "
            "intelligence, timeline, risk, interview and recommendation into one "
            "evidence-backed briefing — with Executive/CTO/CEO/HR/Recruiter/"
            "Committee templates and PDF/DOCX/HTML/PPTX export."
        ),
        input_fields=["candidate_id", "template", "packet", "format"],
        engine="Executive Hiring Report",
    )

    def validate(self, tool_input: Dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("executive_report requires 'candidate_id'.")

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, build the report, and summarize + package it."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        routed = route_request(str(tool_input.get("message", "")))
        template = tool_input.get("template") or routed["template"]
        packet = tool_input.get("packet") or routed["packet"]
        fmt = (tool_input.get("format") or routed["format"] or "pdf").lower()
        if fmt not in FORMATS:
            fmt = "pdf"

        builder = ExecutiveReportBuilder(
            insights_fn=context.insights_fn, ai_runner=_get_runner()
        )
        report = builder.build(candidate=candidate, jd=context.jd, template=template)

        narrative = report.narrative
        export_bytes = b""
        export_error = ""
        try:
            export_bytes = export_report(report, fmt, template)
        except Exception as exc:  # export is best-effort; the report still stands
            export_error = str(exc)

        output = {
            "candidate_id": candidate_id,
            "template": template,
            "template_name": get_template(template).name,
            "packet": packet,
            "format": fmt,
            "overall_recommendation": narrative.overall_recommendation,
            "executive_confidence": narrative.executive_confidence,
            "executive_summary": narrative.executive_summary,
            "business_impact": narrative.business_impact,
            "technical_impact": narrative.technical_impact,
            "risk_overview": narrative.risk_overview,
            "top_reasons": list(narrative.top_reasons),
            "top_concerns": list(narrative.top_concerns),
            "recommended_action": report.action_plan.primary_action,
            "sections": list(get_template(template).section_ids),
            "available_templates": [t.key for t in TEMPLATES.values()],
            "available_formats": list(FORMATS),
            "export_bytes_len": len(export_bytes),
            "export_suffix": suffix_for(fmt),
            "report_id": report.report_id,
        }
        if export_error:
            output["export_error"] = export_error

        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Executive report ({get_template(template).name}) for {candidate_id}: "
                f"recommends {narrative.overall_recommendation} → action "
                f"'{report.action_plan.primary_action}' "
                f"(confidence {narrative.executive_confidence}). "
                f"{fmt.upper()} export {'ready' if export_bytes else 'unavailable'}."
            ),
            evidence_sources=["Executive Hiring Report"] + report.evidence_sources,
        )
