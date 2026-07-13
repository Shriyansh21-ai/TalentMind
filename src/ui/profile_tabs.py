"""Candidate profile tabs for TalentMind.

Renders the four-tab detail view (Intelligence, Skills & Gap, Career,
Explainability) plus the "Similar Candidates" block, inside a candidate's
expander.

De-duplication applied vs. the original inline code (no functionality lost):
    * The "Professional Summary" is shown once (Intelligence tab) instead of
      twice.
    * The duplicate "⭐ Shortlist" button in the Skills tab is removed; a
      single Shortlist action remains.
    * The redundant numeric match-score metric is dropped from the Skills tab
      (the score is already shown as "Overall Match Score" above the tabs);
      the badge and progress bar are retained.

All business-logic calls (skill-gap engine, both hiring-recommendation
engines, similar-candidate search, pipeline status) are unchanged.
"""

from typing import Any, Dict, List

import streamlit as st

from src.models.candidates import Candidate
from src.intelligence.candidate.models import CandidateIntelligence
from src.hiring.recommendation_model import HiringRecommendation
from src.semantic.similar_candidates import find_similar_candidates
from src.recruiter.pipeline import save_status, get_status
from src.scoring.hiring_recommendation import get_hiring_recommendation


def _render_intelligence_tab(
    candidate: Candidate,
    intel: CandidateIntelligence,
    recommendation: HiringRecommendation,
    summary: List[str],
) -> None:
    """Render the Intelligence tab: scores, hiring recommendation, summary."""
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

    st.subheader("💪 Top Strengths")
    for strength in intel.strengths:
        st.success(strength)

    st.subheader("⚠ Areas to Validate")
    for weakness in intel.weaknesses:
        st.warning(weakness)

    st.subheader("🤖 AI Recruiter Summary")
    st.info("\n\n".join([f"• {x}" for x in summary]))

    st.subheader("Professional Summary")
    st.write(candidate.profile.summary)


def _render_skills_tab(
    candidate: Candidate,
    score: float,
    badge: str,
    explanation: Dict[str, Any],
    gap: Dict[str, Any],
) -> None:
    """Render the Skills & Gap tab: skills, JD gap, recommendation, actions."""
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

    # Rule-based hiring recommendation (distinct from the intelligence-engine
    # recommendation shown in the Intelligence tab).
    recommendation, reason = get_hiring_recommendation(
        score,
        gap["match_percent"],
        explanation.get("red_flag_penalty", 0),
    )

    st.subheader("🎯 Hiring Recommendation")
    if recommendation == "Strong Hire":
        st.success("🟢 Strong Hire")
    elif recommendation == "Interview":
        st.info("🔵 Interview")
    elif recommendation == "Consider":
        st.warning("🟡 Consider")
    else:
        st.error("🔴 Reject")
    st.write(reason)

    st.subheader("Recruiter Actions")

    st.markdown(f"### {badge}")
    st.progress(min(score / 200, 1.0))

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "⭐ Shortlist",
            key=f"short_{candidate.candidate_id}",
        ):
            save_status(candidate.candidate_id, "Shortlisted")
    with c2:
        if st.button(
            "❌ Reject",
            key=f"reject_{candidate.candidate_id}",
        ):
            save_status(candidate.candidate_id, "Rejected")
    with c3:
        if st.button(
            "🎉 Hire",
            key=f"hire_{candidate.candidate_id}",
        ):
            save_status(candidate.candidate_id, "Hired")

    current_status = get_status(candidate.candidate_id)
    st.info(f"Current Status: {current_status}")


def _render_career_tab(candidate: Candidate) -> None:
    """Render the Career tab: chronological career history."""
    st.subheader("Career History")

    if not candidate.career_history:
        st.info("No career history available.")
        return

    for job in candidate.career_history:
        st.markdown(f"### {job.title}")
        st.write(job.company)
        st.write(job.description)
        st.divider()


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


def render_profile_tabs(
    candidate: Candidate,
    score: float,
    badge: str,
    explanation: Dict[str, Any],
    intel: CandidateIntelligence,
    gap: Dict[str, Any],
    summary: List[str],
    recommendation: HiringRecommendation,
) -> None:
    """Render the full four-tab candidate detail view plus similar candidates.

    Args:
        candidate: The candidate being displayed.
        score: The candidate's hybrid match score.
        badge: Precomputed match badge string.
        explanation: Rule-based explainability output.
        intel: Candidate intelligence engine output.
        gap: Skill-gap analysis (``matched`` / ``missing`` / ``match_percent``).
        summary: AI recruiter summary lines.
        recommendation: Intelligence-engine hiring recommendation object.
    """
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🧠 Intelligence",
            "📊 Skills & Gap",
            "💼 Career",
            "📄 Explainability",
        ]
    )

    with tab1:
        _render_intelligence_tab(candidate, intel, recommendation, summary)

    with tab2:
        _render_skills_tab(candidate, score, badge, explanation, gap)

    with tab3:
        _render_career_tab(candidate)

    with tab4:
        st.subheader("Explainability")
        st.json(explanation)

    _render_similar_candidates(candidate)
