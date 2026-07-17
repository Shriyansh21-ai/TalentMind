"""Per-candidate intelligence tools.

Each wraps an existing deterministic engine via the shared insight bundle, so the
copilot reasons over the *same* numbers the rest of TalentMind shows — never a
re-derivation.
"""

from __future__ import annotations

from typing import Any

from src.ai.tools.base import (
    BaseTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
    ToolValidationError,
)
from src.interview.planner import build_interview_plan
from src.scoring.explainability import explain_candidate


def _require_candidate(tool_input: dict[str, Any], context: ToolContext):
    """Resolve and return the referenced candidate, or raise."""
    candidate_id = tool_input.get("candidate_id")
    if not candidate_id:
        raise ToolValidationError("This tool requires 'candidate_id'.")
    candidate = context.repository.get(str(candidate_id))
    if candidate is None:
        raise ToolValidationError(f"Unknown candidate {candidate_id!r}.")
    return candidate


class CandidateIntelligenceTool(BaseTool):
    """Expose the Candidate Intelligence engine output."""

    metadata = ToolMetadata(
        name="candidate_intelligence",
        description="Overall/technical/leadership/experience intelligence scores.",
        input_fields=["candidate_id"],
        engine="Candidate Intelligence Engine",
    )

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = _require_candidate(tool_input, context)
        intel = context.build_insights(candidate).intelligence
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_id": candidate.candidate_id,
                "overall": intel.overall_score,
                "experience": intel.experience_score,
                "technical": intel.technical_score,
                "leadership": intel.leadership_score,
                "career_growth": intel.career_growth_score,
                "learning_velocity": intel.learning_velocity,
                "hiring_risk": intel.hiring_risk,
                "confidence": intel.confidence,
                "recommendation": intel.recommendation,
                "strengths": list(intel.strengths),
                "weaknesses": list(intel.weaknesses),
            },
            summary=(
                f"Overall {intel.overall_score:.0f}/100, technical "
                f"{intel.technical_score:.0f}, recommendation '{intel.recommendation}'."
            ),
            evidence_sources=["Candidate Intelligence engine"],
            confidence=intel.confidence,
        )


class TimelineTool(BaseTool):
    """Expose the Career Timeline Intelligence engine output."""

    metadata = ToolMetadata(
        name="timeline",
        description="Career trajectory: growth, stability, promotions, tenure.",
        input_fields=["candidate_id"],
        engine="Career Timeline Intelligence",
    )

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = _require_candidate(tool_input, context)
        timeline = context.build_insights(candidate).timeline
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_id": candidate.candidate_id,
                "timeline_score": timeline.timeline_score,
                "career_growth_score": timeline.career_growth_score,
                "promotion_count": timeline.promotion_count,
                "average_job_duration": timeline.average_job_duration,
                "job_switches": timeline.job_switches,
                "career_stability": timeline.career_stability,
                "leadership_progression": timeline.leadership_progression,
                "domain_consistency": timeline.domain_consistency,
                "summary": timeline.timeline_summary,
                "strengths": list(timeline.strengths),
                "concerns": list(timeline.concerns),
            },
            summary=timeline.timeline_summary,
            evidence_sources=["Career Timeline Intelligence"],
        )


class RiskTool(BaseTool):
    """Expose the Resume Risk Detection engine output."""

    metadata = ToolMetadata(
        name="risk",
        description="Hiring risk assessment, red flags and validation questions.",
        input_fields=["candidate_id"],
        engine="Resume Risk Detection",
    )

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = _require_candidate(tool_input, context)
        risk = context.build_insights(candidate).risk
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_id": candidate.candidate_id,
                "risk_level": risk.risk_level,
                "risk_score": risk.risk_score,
                "overall_risk": risk.overall_risk,
                "risk_factors": list(risk.risk_factors),
                "red_flags": list(risk.red_flags),
                "validation_questions": list(risk.validation_questions),
                "positive_signals": list(risk.positive_signals),
            },
            summary=f"{risk.risk_level} risk (score {risk.risk_score:.0f}/100).",
            evidence_sources=["Resume Risk Detection"],
        )


class RecommendationTool(BaseTool):
    """Expose the Hiring Recommendation engine output."""

    metadata = ToolMetadata(
        name="recommendation",
        description="Hiring recommendation, reasons, concerns and interview focus.",
        input_fields=["candidate_id"],
        engine="Hiring Recommendation Engine",
    )

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = _require_candidate(tool_input, context)
        rec = context.build_insights(candidate).recommendation
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_id": candidate.candidate_id,
                "recommendation": rec.recommendation,
                "confidence": rec.confidence,
                "fit_score": rec.fit_score,
                "reasons": list(rec.reasons),
                "concerns": list(rec.concerns),
                "interview_focus": list(rec.interview_focus),
                "estimated_offer_level": rec.estimated_offer_level,
                "estimated_salary_band": rec.estimated_salary_band,
            },
            summary=f"Recommendation: {rec.recommendation} ({rec.confidence:.0f}%).",
            evidence_sources=["Hiring Recommendation engine"],
            confidence=rec.confidence,
        )


class InterviewTool(BaseTool):
    """Expose the deterministic Interview Planner output."""

    metadata = ToolMetadata(
        name="interview",
        description="Structured interview plan (topics, questions, focus areas).",
        input_fields=["candidate_id"],
        engine="Interview Intelligence",
    )

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = _require_candidate(tool_input, context)
        insights = context.build_insights(candidate)
        plan = build_interview_plan(insights)
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={
                "candidate_id": candidate.candidate_id,
                "technical_topics": list(plan.technical_topics),
                "system_design_topics": list(plan.system_design_topics),
                "behavioral_questions": list(plan.behavioral_questions),
                "leadership_questions": list(plan.leadership_questions),
                "validation_questions": list(plan.validation_questions),
                "coding_focus": list(plan.coding_focus),
                "risk_followups": list(plan.risk_followups),
            },
            summary=(f"Interview plan with {len(plan.technical_topics)} technical topic(s)."),
            evidence_sources=["Interview Intelligence"],
        )


class ExplainabilityTool(BaseTool):
    """Expose the rule-based ranking explainability output."""

    metadata = ToolMetadata(
        name="explainability",
        description="Rule-based ranking breakdown and reasons for a candidate.",
        input_fields=["candidate_id"],
        engine="Explainability",
    )

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = _require_candidate(tool_input, context)
        explanation = explain_candidate(candidate)
        trimmed = {
            "candidate_id": candidate.candidate_id,
            "total_score": explanation.get("total_score"),
            "skill_score": explanation.get("skill_score"),
            "experience_score": explanation.get("experience_score"),
            "title_score": explanation.get("title_score"),
            "company_score": explanation.get("company_score"),
            "career_score": explanation.get("career_score"),
            "red_flag_penalty": explanation.get("red_flag_penalty"),
            "reasons": explanation.get("reasons", []),
        }
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output=trimmed,
            summary=f"Rule-based total score {trimmed['total_score']}.",
            evidence_sources=["Rule-based explainability"],
        )
