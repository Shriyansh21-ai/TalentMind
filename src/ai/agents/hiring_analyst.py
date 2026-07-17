"""HiringAnalystAgent — the platform's first production agent (Module 9).

It reasons over the deterministic engines' structured output (Candidate
Intelligence, Career Timeline, Risk Detection, Hiring Recommendation, Interview
Plan) and the job description, and produces a narrative :class:`HiringAnalysis`.

It **never** computes or overrides a score — the schema has no numeric fields and
the deterministic composer only restates the evidence. The agent is the proof
that the platform works: implement :class:`BaseAgent`, register a composer for
offline mode, and it is done.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.providers.composers import register_composer
from src.ai.schemas.hiring_analysis import EXECUTIVE_DECISIONS, HiringAnalysis
from src.insights.models import CandidateInsights
from src.interview.models import InterviewPlan


@dataclass
class HiringAnalystInput:
    """Typed input for the HiringAnalystAgent.

    Attributes:
        insights: The shared candidate insight bundle (candidate + intelligence +
            timeline + risk + recommendation + skill gap).
        interview_plan: The deterministic interview plan.
        jd: Raw job-description text (may be empty).
    """

    insights: CandidateInsights
    interview_plan: InterviewPlan
    jd: str = ""


# ---------------------------------------------------------------------------
# Evidence extraction (shared by prompt + composer + cache)
# ---------------------------------------------------------------------------


def _top_skill_names(insights: CandidateInsights, limit: int = 8) -> list[str]:
    """Return the candidate's most-endorsed skill names."""
    skills = sorted(
        insights.candidate.skills,
        key=lambda s: (getattr(s, "endorsements", 0), getattr(s, "duration_months", 0)),
        reverse=True,
    )
    return [s.name for s in skills[:limit]]


def build_evidence(payload: HiringAnalystInput) -> dict[str, Any]:
    """Project the insight bundle + interview plan into an evidence dict."""
    insights = payload.insights
    intel = insights.intelligence
    timeline = insights.timeline
    risk = insights.risk
    rec = insights.recommendation
    plan = payload.interview_plan

    return {
        "candidate": {
            "candidate_id": insights.candidate_id,
            "title": insights.title,
            "company": insights.company,
            "location": insights.location,
            "years_of_experience": insights.years_of_experience,
            "top_skills": _top_skill_names(insights),
        },
        "intelligence": {
            "overall": intel.overall_score,
            "experience": intel.experience_score,
            "technical": intel.technical_score,
            "leadership": intel.leadership_score,
            "career_growth": intel.career_growth_score,
            "learning_velocity": intel.learning_velocity,
            "hiring_risk": intel.hiring_risk,
            "hiring_risk_score": intel.hiring_risk_score,
            "confidence": intel.confidence,
            "recommendation": intel.recommendation,
            "strengths": list(intel.strengths),
            "weaknesses": list(intel.weaknesses),
        },
        "timeline": {
            "timeline_score": timeline.timeline_score,
            "career_growth_score": timeline.career_growth_score,
            "promotion_velocity": timeline.promotion_velocity,
            "career_stability": timeline.career_stability,
            "average_job_duration": timeline.average_job_duration,
            "job_switches": timeline.job_switches,
            "promotion_count": timeline.promotion_count,
            "leadership_progression": timeline.leadership_progression,
            "company_quality_trend": timeline.company_quality_trend,
            "domain_consistency": timeline.domain_consistency,
            "summary": timeline.timeline_summary,
            "strengths": list(timeline.strengths),
            "concerns": list(timeline.concerns),
        },
        "risk": {
            "overall_risk": risk.overall_risk,
            "risk_score": risk.risk_score,
            "risk_level": risk.risk_level,
            "career_consistency": risk.career_consistency,
            "employment_gap_risk": risk.employment_gap_risk,
            "job_hopping_risk": risk.job_hopping_risk,
            "skill_stagnation_risk": risk.skill_stagnation_risk,
            "technical_depth_risk": risk.technical_depth_risk,
            "leadership_risk": risk.leadership_risk,
            "communication_risk": risk.communication_risk,
            "risk_factors": list(risk.risk_factors),
            "red_flags": list(risk.red_flags),
            "validation_questions": list(risk.validation_questions),
            "positive_signals": list(risk.positive_signals),
        },
        "recommendation": {
            "recommendation": rec.recommendation if rec else intel.recommendation,
            "confidence": rec.confidence if rec else intel.confidence,
            "fit_score": rec.fit_score if rec else intel.overall_score,
            "reasons": list(rec.reasons) if rec else [],
            "concerns": list(rec.concerns) if rec else [],
            "interview_focus": list(rec.interview_focus) if rec else [],
            "estimated_offer_level": rec.estimated_offer_level if rec else "",
            "estimated_salary_band": rec.estimated_salary_band if rec else "",
        },
        "skill_gap": {
            "match_percent": insights.skill_match_percent,
            "matched": insights.matched_skills,
            "missing": insights.missing_skills,
        },
        "interview_plan": {
            "technical_topics": list(plan.technical_topics),
            "system_design_topics": list(plan.system_design_topics),
            "behavioral_questions": list(plan.behavioral_questions),
            "leadership_questions": list(plan.leadership_questions),
            "validation_questions": list(plan.validation_questions),
            "deep_dive_topics": list(plan.deep_dive_topics),
            "coding_focus": list(plan.coding_focus),
            "communication_focus": list(plan.communication_focus),
            "risk_followups": list(plan.risk_followups),
        },
    }


# ---------------------------------------------------------------------------
# Deterministic composer (offline / fallback reasoning)
# ---------------------------------------------------------------------------


def _band(score: float) -> str:
    """Map a 0-100 score to a qualitative band adjective."""
    if score >= 80:
        return "strong"
    if score >= 65:
        return "solid"
    if score >= 50:
        return "moderate"
    return "limited"


def _decision_from_recommendation(text: str) -> str:
    """Map an engine recommendation string to an allowed executive decision."""
    lowered = (text or "").lower()
    if "strong hire" in lowered:
        return "Strong Hire"
    for decision in EXECUTIVE_DECISIONS:
        if decision.lower() in lowered:
            return decision
    return "Insufficient Evidence"


def _dedupe(items: list[str], limit: int = 6) -> list[str]:
    """Return de-duplicated, order-preserving, non-empty items up to ``limit``."""
    seen = set()
    out: list[str] = []
    for item in items:
        text = (item or "").strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
        if len(out) >= limit:
            break
    return out


def compose_hiring_analysis(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose a :class:`HiringAnalysis` dict from evidence.

    This is the offline reasoning path: it produces professional narrative purely
    by restating and organizing the deterministic engines' output. It cannot
    hallucinate because every sentence is grounded in a provided value.
    """
    cand = evidence.get("candidate", {})
    intel = evidence.get("intelligence", {})
    timeline = evidence.get("timeline", {})
    risk = evidence.get("risk", {})
    rec = evidence.get("recommendation", {})
    gap = evidence.get("skill_gap", {})
    plan = evidence.get("interview_plan", {})

    title = cand.get("title", "The candidate")
    years = cand.get("years_of_experience", 0)
    overall = intel.get("overall", 0)
    technical = intel.get("technical", 0)
    leadership = intel.get("leadership", 0)
    growth = intel.get("career_growth", 0)
    confidence = intel.get("confidence", 0)
    risk_level = risk.get("risk_level", "Unknown")
    match = gap.get("match_percent", 0)
    matched = gap.get("matched", []) or []
    missing = gap.get("missing", []) or []
    recommendation = rec.get("recommendation", intel.get("recommendation", ""))

    executive_summary = (
        f"{title} brings {years} years of experience with an overall intelligence "
        f"score of {overall:.0f}/100 and {_band(technical)} technical signal. "
        f"The deterministic recommendation is '{recommendation}' at {confidence:.0f}% "
        f"confidence, with {risk_level.lower()} hiring risk and {match:.0f}% JD "
        "skill alignment."
    )

    overall_reasoning = (
        f"Composite intelligence sits at {overall:.0f}/100, driven by "
        f"{_band(technical)} technical ({technical:.0f}), {_band(leadership)} "
        f"leadership ({leadership:.0f}) and {_band(growth)} career growth "
        f"({growth:.0f}). "
        + (
            "Supporting reasons: " + "; ".join(rec.get("reasons", [])) + ". "
            if rec.get("reasons")
            else ""
        )
        + (
            "Noted concerns: " + "; ".join(rec.get("concerns", [])) + "."
            if rec.get("concerns")
            else "No blocking concerns were flagged by the engines."
        )
    )

    technical_reasoning = (
        f"Technical capability scores {technical:.0f}/100 ({_band(technical)}). "
        f"Demonstrated strengths include {', '.join(cand.get('top_skills', [])[:5]) or 'the listed skills'}. "
        + (
            f"Relative to the role, {len(missing)} JD skill(s) are not evidenced "
            f"({', '.join(missing)}) and should be probed."
            if missing
            else "All targeted JD skills are evidenced in the profile."
        )
    )

    career_reasoning = (
        f"{timeline.get('summary', 'Career trajectory analysed by the timeline engine.')} "
        f"Timeline score is {timeline.get('timeline_score', 0):.0f}/100 with "
        f"{timeline.get('promotion_count', 0)} promotion(s), average tenure of "
        f"{timeline.get('average_job_duration', 0):.0f} months and a "
        f"'{timeline.get('leadership_progression', 'n/a')}' progression pattern."
    )

    leadership_reasoning = (
        f"Leadership signal is {_band(leadership)} ({leadership:.0f}/100). "
        f"The trajectory shows a '{timeline.get('leadership_progression', 'n/a')}' "
        "pattern. "
        + (
            "This supports scope beyond individual contribution."
            if leadership >= 65
            else "Validate the breadth of ownership and people-leadership in interview."
        )
    )

    risk_reasoning = (
        f"Overall risk is {risk_level} (score {risk.get('risk_score', 0):.0f}/100). "
        + (
            "Key factors: " + "; ".join(risk.get("risk_factors", [])) + ". "
            if risk.get("risk_factors")
            else "No material risk factors were surfaced. "
        )
        + (
            "Red flags to address: " + "; ".join(risk.get("red_flags", [])) + "."
            if risk.get("red_flags")
            else "No red flags were detected."
        )
    )

    jd_alignment = (
        f"The candidate matches {match:.0f}% of the targeted JD skills. "
        + (f"Matched: {', '.join(matched)}. " if matched else "")
        + (
            f"Gaps: {', '.join(missing)} — weigh these against the seniority of the role."
            if missing
            else "No JD skill gaps were identified."
        )
    )

    hidden_strengths = _dedupe(
        list(timeline.get("strengths", []))
        + list(risk.get("positive_signals", []))
        + list(intel.get("strengths", []))
    )
    hidden_concerns = _dedupe(
        list(intel.get("weaknesses", []))
        + list(timeline.get("concerns", []))
        + list(risk.get("risk_factors", []))
    )
    transferable_skills = _dedupe(list(matched) + list(cand.get("top_skills", [])))

    interview_strategy = _dedupe(
        list(plan.get("technical_topics", []))
        + list(plan.get("system_design_topics", []))
        + list(plan.get("risk_followups", [])),
        limit=8,
    )

    business_impact = (
        f"With {_band(technical)} technical depth and {_band(leadership)} leadership "
        f"over {years} years, the expected impact is "
        + (
            "high — able to own significant scope and mentor others."
            if overall >= 75
            else "moderate — productive with the right onboarding and validation of the noted gaps."
            if overall >= 55
            else "uncertain — the evidence does not yet support a confident impact projection."
        )
    )

    low_conf = confidence < 55 or risk_level == "High"
    confidence_reasoning = f"Engine confidence is {confidence:.0f}%. " + (
        "Evidence is limited or risk is elevated, so this analysis is stated "
        "with explicit uncertainty; prioritise the validation questions before "
        "deciding."
        if low_conf
        else "The signals are consistent across engines, supporting a confident read."
    )

    return {
        "executive_summary": executive_summary,
        "overall_reasoning": overall_reasoning,
        "technical_reasoning": technical_reasoning,
        "career_reasoning": career_reasoning,
        "leadership_reasoning": leadership_reasoning,
        "risk_reasoning": risk_reasoning,
        "jd_alignment": jd_alignment,
        "hidden_strengths": hidden_strengths,
        "hidden_concerns": hidden_concerns,
        "transferable_skills": transferable_skills,
        "interview_strategy": interview_strategy,
        "business_impact": business_impact,
        "confidence_reasoning": confidence_reasoning,
        "executive_decision": _decision_from_recommendation(recommendation),
    }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class HiringAnalystAgent(BaseAgent):
    """Narrative hiring analyst that reasons over deterministic intelligence."""

    metadata = AgentMetadata(
        name="hiring_analyst",
        version="v1",
        title="AI Hiring Analyst",
        description=(
            "Reasons over deterministic candidate intelligence to produce an "
            "executive-quality hiring analysis. Never computes or alters scores."
        ),
        prompt_id="hiring_analyst",
        prompt_version="v1",
        tags=["hiring", "analysis", "candidate"],
    )
    output_schema = HiringAnalysis

    def build_evidence(self, payload: HiringAnalystInput) -> dict[str, Any]:
        """Return the structured evidence for ``payload`` (see module function)."""
        return build_evidence(payload)

    def prompt_values(
        self, payload: HiringAnalystInput, evidence: dict[str, Any]
    ) -> dict[str, str]:
        """Supply the ``jd`` placeholder for the user prompt."""
        return {"jd": payload.jd.strip() or "(No job description provided.)"}

    def cache_dimensions(self, payload: HiringAnalystInput) -> tuple[str, str]:
        """Cache by candidate id (subject) and job description (scope)."""
        return payload.insights.candidate_id, payload.jd or ""


# Register the deterministic composer + the agent at import time so the platform
# is ready with zero external configuration.
register_composer(HiringAnalysis.schema_name(), compose_hiring_analysis)
hiring_analyst_agent = registry.register(HiringAnalystAgent())
