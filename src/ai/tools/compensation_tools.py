"""Compensation Governance tool for the Recruiter Copilot (Module 13).

Exposes the :class:`CompensationGovernanceEngine` to the copilot as a standard
:class:`BaseTool`. Selected by intent, so the copilot *automatically* answers
"why are we offering this compensation?", "generate compensation report", "show
offer justification", "create finance approval report", "explain executive
reasoning" and "what is the negotiation strategy?". The report consumes only
existing structured outputs and reuses the AI Platform, committee and
orchestration frameworks (Module 15). It fabricates no salary or market data.
"""

from __future__ import annotations

from typing import Any

# Importing the engine auto-registers the agent (AI platform + orchestration).
from src.ai.agents.compensation.governance import CompensationGovernanceEngine
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
    """Return a shared, lazily-created :class:`AgentRunner`."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


class CompensationGovernanceTool(BaseTool):
    """Generate a transparent, defensible compensation governance report for a candidate."""

    metadata = ToolMetadata(
        name="compensation_governance",
        description=(
            "Generate an enterprise compensation governance report: a defensible "
            "salary range (never a fixed figure), an offer-justification audit "
            "trail, governance checks, market position, offer scenarios, "
            "negotiation strategy, budget assessment, internal-equity readiness, "
            "future outlook and a flagship transparency audit trail — all from "
            "existing intelligence, fabricating no salary or market data."
        ),
        input_fields=["candidate_id"],
        engine="Compensation Governance",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("compensation_governance requires 'candidate_id'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, build the governance report, and summarize it."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        engine = CompensationGovernanceEngine(
            insights_fn=context.insights_fn, ai_runner=_get_runner()
        )
        report = engine.build(candidate=candidate, jd=context.jd)

        band = report.recommended_range
        narrative = report.narrative
        audit = report.audit_trail
        output = {
            "candidate_id": candidate_id,
            "recommended_range": band.formatted(),
            "range_min": band.minimum,
            "range_target": band.target,
            "range_max": band.maximum,
            "currency": band.currency,
            "unit": band.unit,
            "confidence": band.confidence_label,
            "market_position": report.market_position.position,
            "market_data_note": report.market_position.data_note,
            "hire_type": report.budget.hire_type,
            "executive_summary": narrative.executive_summary,
            "recommendation_rationale": narrative.recommendation_rationale,
            "key_justifications": list(narrative.key_justifications),
            "key_assumptions": list(narrative.key_assumptions),
            "scenarios": [
                {"name": s.name, "target": s.comp_range.target, "range": s.comp_range.formatted()}
                for s in report.scenarios
            ],
            "acceptance_likelihood": report.negotiation.acceptance_likelihood,
            "negotiation_probability": report.negotiation.negotiation_probability,
            "negotiation_strategy": list(report.negotiation.strategy),
            "recruiter_talking_points": list(report.negotiation.recruiter_talking_points),
            "governance_checks": [
                {"dimension": c.dimension, "status": c.status} for c in report.governance_checks
            ],
            "internal_equity": report.internal_equity.status_message,
            "internal_equity_available": report.internal_equity.available,
            "audit_decision_id": audit.decision_id,
            "approvals_required": list(audit.approvals_required),
            "human_review_status": audit.human_review_status,
            "agents_consulted": list(audit.agents_consulted),
            "report_id": report.report_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Compensation governance for {candidate_id}: recommends "
                f"{band.formatted()} ({report.market_position.position}, "
                f"{report.budget.hire_type}, {band.confidence_label} confidence). "
                f"Acceptance likelihood {report.negotiation.acceptance_likelihood}. "
                f"Decision {audit.decision_id} needs {', '.join(audit.approvals_required)} "
                f"({audit.human_review_status})."
            ),
            evidence_sources=["Compensation Governance"] + report.evidence_sources,
        )
