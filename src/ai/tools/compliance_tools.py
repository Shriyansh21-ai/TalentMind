"""Hiring Compliance tool for the Recruiter Copilot (Module 11).

Exposes the :class:`HiringComplianceEngine` to the copilot as a standard
:class:`BaseTool`. Selected by intent, so the copilot *automatically* answers
"is this hiring process compliant?", "generate compliance report", "what
approvals are missing?", "show audit trail", "is executive approval required?"
and "what documentation is missing?". It reuses the whole intelligence chain
(Module 13), gives no legal advice and fabricates no compliance conclusion
(Module 14).
"""

from __future__ import annotations

from typing import Any

# Importing the engine auto-registers the agent (AI platform + orchestration).
from src.ai.agents.compliance.compliance_report import HiringComplianceEngine
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


class HiringComplianceTool(BaseTool):
    """Evaluate whether a candidate's hiring workflow follows company governance."""

    metadata = ToolMetadata(
        name="hiring_compliance",
        description=(
            "Evaluate whether a hiring workflow follows company governance: "
            "required workflow steps, approval completeness, configurable policy "
            "compliance, documentation presence, audit-trail readiness, governance "
            "risk and whether Legal/Compliance should review. Reuses the whole "
            "intelligence chain; reports items needing an external system as "
            "pending review. Surfaces governance risks only — never legal advice."
        ),
        input_fields=["candidate_id"],
        engine="Hiring Compliance",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("hiring_compliance requires 'candidate_id'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, build the compliance report, and summarize it."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        engine = HiringComplianceEngine(insights_fn=context.insights_fn, ai_runner=_get_runner())
        report = engine.build(candidate=candidate, jd=context.jd)

        narrative = report.narrative
        output = {
            "candidate_id": candidate_id,
            "data_available": report.data_available,
            "workflow_status": report.workflow.status,
            "workflow_completed": report.workflow.completed,
            "workflow_total": report.workflow.total,
            "required_approvals": report.approvals.required(),
            "outstanding_approvals": report.approvals.outstanding(),
            "missing_documentation": report.documentation.missing(),
            "audit_status": report.audit.status,
            "governance_risk": report.governance_risk.level,
            "policy_checks": [
                {"policy": p.policy_name, "status": p.status} for p in report.policy_checks
            ],
            "exceptions": [{"kind": e.kind, "severity": e.severity} for e in report.exceptions],
            "legal_review_recommended": report.review.legal_review_recommended,
            "compliance_review_recommended": report.review.compliance_review_recommended,
            "reviewers": report.review.reviewers,
            "executive_summary": narrative.executive_summary,
            "required_actions": list(narrative.required_actions),
            "key_findings": list(narrative.key_findings),
            "human_review_recommendations": list(narrative.human_review_recommendations),
            "report_id": report.report_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Hiring compliance for {candidate_id}: workflow {report.workflow.status} "
                f"({report.workflow.completed}/{report.workflow.total}), governance risk "
                f"{report.governance_risk.level}, audit {report.audit.status}. "
                + (
                    f"Outstanding approvals: {', '.join(report.approvals.outstanding())}. "
                    if report.approvals.outstanding()
                    else ""
                )
                + (
                    f"Recommend {', '.join(report.review.reviewers)} review. "
                    if report.review.reviewers
                    else ""
                )
                + "Governance assessment only; not legal advice."
            ),
            evidence_sources=["Hiring Compliance"] + report.evidence_sources,
        )
