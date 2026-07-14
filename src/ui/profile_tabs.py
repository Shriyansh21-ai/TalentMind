"""Candidate profile tabs for TalentMind.

Coordinates the full candidate detail view. As of Phase 2 / Milestone 1 the
profile is organized into nine tabs:

    Summary · Candidate Intelligence · Career Timeline · Risk Analysis ·
    Skills · Career History · Explainability · Hiring Recommendation ·
    Interview Plan (placeholder)

plus a "Similar Candidates" block rendered beneath the tabs.

No existing feature was removed — the previous four-tab content was
redistributed into the new structure, and the Career Timeline / Risk Analysis
tabs were added. All business-logic calls (skill-gap, both hiring-recommendation
engines, similar-candidate search, pipeline status, timeline & risk engines)
are unchanged and injected precomputed by ``candidate_card``.
"""

from typing import Any, Dict, List, Optional

import streamlit as st

from src.models.candidates import Candidate
from src.intelligence.candidate.models import CandidateIntelligence
from src.intelligence.timeline.models import CareerTimelineAnalysis
from src.intelligence.risk.models import RiskReport
from src.hiring.recommendation_model import HiringRecommendation
from src.interview.models import InterviewPlan
from src.semantic.similar_candidates import find_similar_candidates
from src.recruiter.pipeline import save_status, get_status
from src.scoring.hiring_recommendation import get_hiring_recommendation
from src.ui.timeline_tab import render_timeline_tab
from src.ui.risk_tab import render_risk_tab
from src.ui.interview_tab import render_interview_tab


# ---------------------------------------------------------------------------
# Individual tab renderers
# ---------------------------------------------------------------------------


def _render_summary_tab(candidate: Candidate, summary: List[str]) -> None:
    """Render the Summary tab: AI recruiter summary + professional summary."""
    st.subheader("🤖 AI Recruiter Summary")
    if summary:
        st.info("\n\n".join([f"• {x}" for x in summary]))
    else:
        st.caption("No AI summary available for this candidate.")

    st.subheader("Professional Summary")
    st.write(candidate.profile.summary)


def _render_intelligence_tab(intel: CandidateIntelligence) -> None:
    """Render the Candidate Intelligence tab (engine output, unchanged)."""
    st.subheader("🧠 Candidate Intelligence")

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall", f"{intel.overall_score:.1f}%")
    c2.metric("Recommendation", intel.recommendation)
    c3.metric("Confidence", f"{intel.confidence:.1f}%")

    d1, d2, d3 = st.columns(3)
    d1.metric("Experience", f"{intel.experience_score:.1f}")
    d2.metric("Technical", f"{intel.technical_score:.1f}")
    d3.metric("Leadership", f"{intel.leadership_score:.1f}")

    e1, e2, e3 = st.columns(3)
    e1.metric("Career Growth", f"{intel.career_growth_score:.1f}")
    e2.metric("Learning", f"{intel.learning_velocity:.1f}")
    e3.metric("Hiring Risk", intel.hiring_risk)

    st.progress(intel.overall_score / 100)

    st.subheader("💪 Top Strengths")
    for strength in intel.strengths:
        st.success(strength)

    st.subheader("⚠ Areas to Validate")
    for weakness in intel.weaknesses:
        st.warning(weakness)


def _render_skills_tab(candidate: Candidate, gap: Dict[str, Any]) -> None:
    """Render the Skills tab: skill list + JD gap analysis."""
    st.subheader("Skills")

    skills = [s.name for s in candidate.skills]
    if skills:
        st.write(", ".join(skills))
    else:
        st.info("No skills listed for this candidate.")

    st.subheader("JD Gap Analysis")

    a, b = st.columns(2)
    with a:
        st.success(f"Matched Skills ({len(gap['matched'])})")
        for skill in gap["matched"]:
            st.write("✅", skill)
    with b:
        st.error(f"Missing Skills ({len(gap['missing'])})")
        for skill in gap["missing"]:
            st.write("❌", skill)

    st.progress(gap["match_percent"] / 100)
    st.write(f"Skill Match: {gap['match_percent']}%")


def _render_career_tab(candidate: Candidate) -> None:
    """Render the Career History tab (chronological role list)."""
    st.subheader("Career History")

    if not candidate.career_history:
        st.info("No career history available.")
        return

    for job in candidate.career_history:
        st.markdown(f"### {job.title}")
        st.write(job.company)
        st.write(job.description)
        st.divider()


def _render_hiring_tab(
    candidate: Candidate,
    score: float,
    badge: str,
    explanation: Dict[str, Any],
    gap: Dict[str, Any],
    recommendation: HiringRecommendation,
) -> None:
    """Render the Hiring Recommendation tab.

    Combines the intelligence-engine recommendation, the rule-based
    recommendation, and the recruiter action controls — all preserved from the
    original profile.
    """
    # --- Intelligence-engine recommendation --------------------------------
    st.subheader("🎯 Hiring Recommendation")

    if "Strong Hire" in recommendation.recommendation:
        st.success(recommendation.recommendation)
    elif "Hire" in recommendation.recommendation:
        st.info(recommendation.recommendation)
    elif "Hold" in recommendation.recommendation:
        st.warning(recommendation.recommendation)
    else:
        st.error(recommendation.recommendation)

    a, b = st.columns(2)
    with a:
        st.metric("Hiring Confidence", f"{recommendation.confidence}%")
    with b:
        st.metric("Predicted Role", recommendation.estimated_offer_level)

    st.metric("Estimated Salary", recommendation.estimated_salary_band)

    left, right = st.columns(2)
    with left:
        st.markdown("### ✅ Hiring Reasons")
        for reason in recommendation.reasons:
            st.success(reason)
    with right:
        st.markdown("### ⚠ Interview Focus")
        for topic in recommendation.interview_focus:
            st.info(topic)

    if recommendation.concerns:
        st.markdown("### 🚨 Concerns")
        for concern in recommendation.concerns:
            st.warning(concern)

    st.divider()

    # --- Rule-based recommendation (distinct engine) -----------------------
    rule_recommendation, reason = get_hiring_recommendation(
        score,
        gap["match_percent"],
        explanation.get("red_flag_penalty", 0),
    )

    st.subheader("🧮 Rule-Based Recommendation")
    if rule_recommendation == "Strong Hire":
        st.success("🟢 Strong Hire")
    elif rule_recommendation == "Interview":
        st.info("🔵 Interview")
    elif rule_recommendation == "Consider":
        st.warning("🟡 Consider")
    else:
        st.error("🔴 Reject")
    st.write(reason)

    st.divider()

    # --- Recruiter actions -------------------------------------------------
    st.subheader("Recruiter Actions")

    st.markdown(f"### {badge}")
    st.progress(min(score / 200, 1.0))

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⭐ Shortlist", key=f"short_{candidate.candidate_id}"):
            save_status(candidate.candidate_id, "Shortlisted")
    with c2:
        if st.button("❌ Reject", key=f"reject_{candidate.candidate_id}"):
            save_status(candidate.candidate_id, "Rejected")
    with c3:
        if st.button("🎉 Hire", key=f"hire_{candidate.candidate_id}"):
            save_status(candidate.candidate_id, "Hired")

    current_status = get_status(candidate.candidate_id)
    st.info(f"Current Status: {current_status}")


def _render_interview_plan_tab(
    interview_plan: Optional[InterviewPlan],
    recommendation: HiringRecommendation,
) -> None:
    """Render the Interview Plan tab.

    As of Phase 2 / Milestone 2 this renders a full, deterministic
    :class:`InterviewPlan` (Module 4). If no plan is supplied (e.g. a legacy
    caller), it falls back to surfacing the recommendation's interview focus.
    """
    if interview_plan is not None:
        render_interview_tab(interview_plan)
        return

    st.subheader("🗓 Interview Plan")
    if recommendation.interview_focus:
        st.markdown("### Suggested Focus Areas")
        for topic in recommendation.interview_focus:
            st.write("•", topic)


def _render_similar_candidates(candidate: Candidate) -> None:
    """Render the "Similar Candidates" block; fail silently if unavailable."""
    try:
        st.subheader("Similar Candidates")

        sims = find_similar_candidates(candidate, top_k=3)

        for sim in sims:
            if sim.candidate_id == candidate.candidate_id:
                continue
            st.write(
                f"🔹 {sim.profile.current_title} | "
                f"{sim.profile.current_company}"
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_profile_tabs(
    candidate: Candidate,
    score: float,
    badge: str,
    explanation: Dict[str, Any],
    intel: CandidateIntelligence,
    gap: Dict[str, Any],
    summary: List[str],
    recommendation: HiringRecommendation,
    timeline: CareerTimelineAnalysis,
    risk: RiskReport,
    interview_plan: Optional[InterviewPlan] = None,
) -> None:
    """Render the full nine-tab candidate detail view plus similar candidates.

    Args:
        candidate: The candidate being displayed.
        score: The candidate's hybrid match score.
        badge: Precomputed match badge string.
        explanation: Rule-based explainability output.
        intel: Candidate intelligence engine output.
        gap: Skill-gap analysis (``matched`` / ``missing`` / ``match_percent``).
        summary: AI recruiter summary lines.
        recommendation: Intelligence-engine hiring recommendation object.
        timeline: Career timeline analysis (new in Milestone 1).
        risk: Resume risk report (new in Milestone 1).
        interview_plan: Deterministic interview plan (Module 4). When provided the
            Interview Plan tab renders the full structured plan; otherwise it
            falls back to the recommendation's focus areas.
    """
    (
        tab_summary,
        tab_intel,
        tab_timeline,
        tab_risk,
        tab_skills,
        tab_career,
        tab_explain,
        tab_hiring,
        tab_interview,
    ) = st.tabs(
        [
            "📄 Summary",
            "🧠 Candidate Intelligence",
            "📈 Career Timeline",
            "🚨 Risk Analysis",
            "📊 Skills",
            "💼 Career History",
            "📄 Explainability",
            "🎯 Hiring Recommendation",
            "🗓 Interview Plan",
        ]
    )

    with tab_summary:
        _render_summary_tab(candidate, summary)

    with tab_intel:
        _render_intelligence_tab(intel)

    with tab_timeline:
        render_timeline_tab(timeline)

    with tab_risk:
        render_risk_tab(risk)

    with tab_skills:
        _render_skills_tab(candidate, gap)

    with tab_career:
        _render_career_tab(candidate)

    with tab_explain:
        st.subheader("Explainability")
        st.json(explanation)

    with tab_hiring:
        _render_hiring_tab(candidate, score, badge, explanation, gap, recommendation)

    with tab_interview:
        _render_interview_plan_tab(interview_plan, recommendation)

    _render_similar_candidates(candidate)
