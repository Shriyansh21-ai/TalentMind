"""Hiring Audit tool for the Recruiter Copilot (Module 11).

Exposes the :class:`HiringAuditEngine` to the copilot as a standard
:class:`BaseTool`. Selected by intent, so the copilot *automatically* answers
"why was this candidate hired?", "explain this hiring decision", "show decision
timeline", "show evidence", "generate audit report" and "show approval history".
It reuses the whole intelligence chain (Module 13), reconstructs only what is on
record and never fabricates evidence/approvals/history (Module 14).
"""

from __future__ import annotations

from typing import Any

# Importing the engine auto-registers the agent (AI platform + orchestration).
from src.ai.agents.audit.audit_engine import HiringAuditEngine
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


class HiringAuditTool(BaseTool):
    """Reconstruct + explain the complete hiring decision journey for a candidate."""

    metadata = ToolMetadata(
        name="hiring_audit",
        description=(
            "Reconstruct the complete hiring journey: the decision trace, evidence "
            "provenance, evidence graph, reasoning, timeline, human-vs-AI "
            "responsibility, governance explanations and audit readiness. Reuses "
            "the whole intelligence chain; reconstructs only what is on record and "
            "reports unavailable history/approvals honestly — never fabricates and "
            "never issues a legal opinion."
        ),
        input_fields=["candidate_id"],
        engine="Hiring Audit",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        """Require a candidate id."""
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("hiring_audit requires 'candidate_id'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        """Resolve the candidate, reconstruct the journey, and summarize it."""
        candidate_id = str(tool_input["candidate_id"])
        candidate = context.repository.get(candidate_id)
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")

        engine = HiringAuditEngine(insights_fn=context.insights_fn, ai_runner=_get_runner())
        report = engine.build(candidate=candidate, jd=context.jd)

        narrative = report.narrative
        readiness = report.audit_readiness
        ai_decisions = [
            d
            for d in report.responsibility
            if d.responsible_party == "AI" and d.status == "Observed"
        ]
        human_verified = [
            d
            for d in report.responsibility
            if d.responsible_party != "AI" and d.status == "Observed"
        ]
        output = {
            "candidate_id": candidate_id,
            "data_available": report.data_available,
            "agents_participated": list(report.agents_participated),
            "agent_count": len(report.agents_participated),
            "decision_trace": [
                {"stage": s.stage, "status": s.status} for s in report.decision_trace
            ],
            "timeline": [
                {"name": t.name, "actor": t.actor, "status": t.status} for t in report.timeline
            ],
            "ai_decisions": [d.decision for d in ai_decisions],
            "human_decisions_verified": [d.decision for d in human_verified],
            "outstanding_approvals": list(readiness.missing_approvals),
            "audit_readiness": readiness.status,
            "readiness_level": readiness.readiness_level,
            "missing_evidence": list(readiness.missing_evidence),
            "governance_explanations": [
                {"topic": g.topic, "explanation": g.explanation}
                for g in report.governance_explanations
            ],
            "history_available": report.history.available,
            "executive_summary": narrative.executive_summary,
            "key_findings": list(narrative.key_findings),
            "outstanding_risks": list(narrative.outstanding_risks),
            "audit_recommendations": list(narrative.audit_recommendations),
            "report_id": report.report_id,
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=output,
            summary=(
                f"Hiring audit for {candidate_id}: {len(report.agents_participated)} agent(s) participated, "
                f"audit readiness {readiness.status} ({readiness.readiness_level}). "
                f"{len(ai_decisions)} AI decision(s), {len(human_verified)} verified human approval(s). "
                + (
                    f"Outstanding: {', '.join(readiness.missing_approvals)}. "
                    if readiness.missing_approvals
                    else ""
                )
                + "Reconstructed from artefacts on record; no fabrication, no legal opinion."
            ),
            evidence_sources=["Hiring Audit"] + report.evidence_sources,
        )
