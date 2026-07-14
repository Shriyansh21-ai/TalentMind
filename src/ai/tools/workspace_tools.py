"""Workspace-level tools: comparison, pipeline and dashboard.

These wrap the Phase-2 enterprise-workspace engines (comparison builder, pipeline
store, dashboard analytics) so the copilot can answer multi-candidate and
aggregate questions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.comparison.builder import build_comparison
from src.dashboard import analytics
from src.pipeline.store import PipelineStore
from src.ai.tools.base import (
    BaseTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
    ToolValidationError,
)


class ComparisonTool(BaseTool):
    """Compare up to five candidates (wraps the comparison builder)."""

    metadata = ToolMetadata(
        name="comparison",
        description="Side-by-side comparison of up to 5 candidates.",
        input_fields=["candidate_ids"],
        engine="Candidate Comparison",
    )

    def validate(self, tool_input: Dict[str, Any]) -> None:
        ids = tool_input.get("candidate_ids") or []
        if len(ids) < 2:
            raise ToolValidationError(
                "comparison requires at least 2 'candidate_ids'."
            )

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        ids: List[str] = list(tool_input["candidate_ids"])[:5]
        insights = []
        resolved: List[str] = []
        for candidate_id in ids:
            candidate = context.repository.get(str(candidate_id))
            if candidate is not None:
                insights.append(context.build_insights(candidate))
                resolved.append(candidate.candidate_id)

        if len(insights) < 2:
            raise ToolValidationError(
                "Could not resolve at least 2 candidates to compare."
            )

        report = build_comparison(insights)
        rows = [
            {
                "candidate_id": r.candidate_id,
                "title": r.title,
                "overall_score": r.overall_score,
                "technical_score": r.technical_score,
                "leadership_score": r.leadership_score,
                "experience_score": r.experience_score,
                "timeline_score": r.timeline_score,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "skill_match": r.skill_match,
                "hiring_recommendation": r.hiring_recommendation,
            }
            for r in report.rows
        ]
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_ids": resolved,
                "rows": rows,
                "best_by_metric": report.best_by_metric,
            },
            summary=f"Compared {len(rows)} candidates across all metrics.",
            evidence_sources=["Candidate Comparison engine"],
        )


class PipelineTool(BaseTool):
    """Read hiring-pipeline state (wraps the pipeline store)."""

    metadata = ToolMetadata(
        name="pipeline",
        description="Pipeline stage/status for a candidate, or overall funnel.",
        input_fields=["candidate_id"],
        engine="Hiring Pipeline",
    )

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        store = PipelineStore()
        states = store.load()
        candidate_id = tool_input.get("candidate_id")

        if candidate_id:
            status = states.get(str(candidate_id))
            if status is None:
                return ToolResult(
                    name=self.metadata.name,
                    ok=True,
                    output={"candidate_id": candidate_id, "tracked": False},
                    summary="Candidate is not yet in the hiring pipeline.",
                    evidence_sources=["Hiring Pipeline"],
                )
            return ToolResult(
                name=self.metadata.name,
                ok=True,
                output={
                    "candidate_id": candidate_id,
                    "tracked": True,
                    "current_stage": status.current_stage.value,
                    "status": status.status,
                    "priority": status.priority.value,
                    "assigned_recruiter": status.assigned_recruiter,
                    "notes": list(status.notes[-5:]),
                },
                summary=(
                    f"Candidate is at '{status.current_stage.value}' "
                    f"({status.status})."
                ),
                evidence_sources=["Hiring Pipeline"],
            )

        distribution = analytics.stage_distribution(list(states.values()))
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={"tracked_candidates": len(states), "stage_distribution": distribution},
            summary=f"{len(states)} candidate(s) tracked in the pipeline.",
            evidence_sources=["Hiring Pipeline"],
        )


class DashboardTool(BaseTool):
    """Aggregate cohort analytics (wraps the dashboard analytics)."""

    metadata = ToolMetadata(
        name="dashboard",
        description="Aggregate stats: experience, top skills, locations, companies.",
        input_fields=[],
        engine="Recruiter Dashboard",
    )

    def execute(self, tool_input: Dict[str, Any], context: ToolContext) -> ToolResult:
        candidates = context.repository.sample(limit=500)
        states = list(PipelineStore().load().values())
        experience = analytics.experience_distribution(candidates)
        avg_exp = round(sum(experience) / len(experience), 1) if experience else 0.0
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_count": len(candidates),
                "average_experience": avg_exp,
                "top_skills": analytics.top_skills(candidates, limit=10),
                "top_locations": analytics.location_distribution(candidates, limit=8),
                "top_companies": analytics.company_distribution(candidates, limit=8),
                "stage_distribution": analytics.stage_distribution(states),
            },
            summary=(
                f"Cohort of {len(candidates)} candidates, avg experience "
                f"{avg_exp} yrs."
            ),
            evidence_sources=["Recruiter Dashboard analytics"],
        )
