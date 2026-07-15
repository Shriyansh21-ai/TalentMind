"""Pay Equity Guardian tool for the Recruiter Copilot (Module 11).

Exposes the :class:`PayEquityGuardianEngine` to the copilot as a standard
:class:`BaseTool`. Selected by intent, so the copilot *automatically* answers
"is this offer fair?", "check internal equity", "show compression risk", "who
should approve this?", "does this violate pay policy?" and "generate pay equity
report". It reuses the Compensation Governance Agent + existing intelligence
(Module 13) and fabricates no payroll or legal conclusion (Module 14).
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
from src.ai.agents.pay_equity.equity_engine import PayEquityGuardianEngine
from src.ai.agents.pay_equity.templates import PAY_POLICIES

_runner: Optional[AgentRunner] = None


def _get_runner() -> AgentRunner:
    """Return a shared, lazily-created :class:`AgentRunner`."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


def route_policy(message: str) -> str:
    """Infer a pay-policy key from a free-text copilot message (empty = default)."""
    text = (message or "").lower()
    for key, policy in PAY_POLICIES.items():
        if key.replace("_", " ") in text or policy.name.lower() in text:
            return key
    return ""


class PayEquityTool(BaseTool):
    """Evaluate the internal pay-equity / fairness of a candidate's offer."""

    metadata = ToolMetadata(
        name="pay_equity_guardian",
        description=(
            "Evaluate whether an offer is internally fair: salary compression, pay "
            "inversion, promotion equity, company pay-policy alignment and which "
            "approvers are required. Reuses the Compensation Governance offer and "
            "existing intelligence; reports internal comparisons as unavailable when "
            "no HRIS data is connected. Surfaces governance risks and review needs "
            "only — never fabricates payroll and never concludes a legal violation."
        ),
        input_fields=["candidate_id", "policy"],
        engine="Pay Equity Guardian",
    )

    def validate(self, tool_input: Dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("pay_equity_guardian requires 'candidate_id'.")

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, build the pay-equity report, and summarize it."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        policy = tool_input.get("policy") or route_policy(str(tool_input.get("message", "")))
        engine = PayEquityGuardianEngine(insights_fn=context.insights_fn, ai_runner=_get_runner())
        report = engine.build(candidate=candidate, jd=context.jd, policy=policy)

        narrative = report.narrative
        er = report.executive_review
        output = {
            "candidate_id": candidate_id,
            "data_available": report.data_available,
            "offer": report.offer_summary.get("recommended_range", ""),
            "policy": report.policy_alignment.policy_name,
            "policy_alignment": report.policy_alignment.alignment,
            "policy_violations": list(report.policy_alignment.violations),
            "equity_risk": report.equity_risk.level,
            "compression_risk": report.compression.risk_level,
            "compression_rationale": report.compression.rationale,
            "inversion_risk": report.inversion.risk_level,
            "inversion_rationale": report.inversion.rationale,
            "promotion_consistency": report.promotion.consistency,
            "review_level": er.review_level,
            "required_approvers": er.required_approvers(),
            "executive_summary": narrative.executive_summary,
            "fairness_note": narrative.fairness_note,
            "key_findings": list(narrative.key_findings),
            "human_review_recommendations": list(narrative.human_review_recommendations),
            "data_availability_note": narrative.data_availability_note,
            "scenarios": [
                {"name": s.name, "target": s.offer_target, "equity_impact": s.equity_impact}
                for s in report.scenarios
            ],
            "report_id": report.report_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Pay-equity review for {candidate_id}: equity risk {report.equity_risk.level}"
                + (" (no internal data — provisional)" if not report.data_available else "")
                + f"; compression {report.compression.risk_level}, inversion {report.inversion.risk_level}. "
                f"Policy '{report.policy_alignment.policy_name}' {report.policy_alignment.alignment}. "
                f"{er.review_level} review — approvers: {', '.join(er.required_approvers())}. "
                "Governance assessment only; no legal conclusion."
            ),
            evidence_sources=["Pay Equity Guardian"] + report.evidence_sources,
        )
