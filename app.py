# app.py

import os
import json
import pandas as pd
import streamlit as st

from llm.recruiter_summary import generate_summary
import rank
from src.ingestion.candidate_loader import load_candidates

from src.scoring.final_score import calculate_final_score
from src.scoring.hybrid_score import hybrid_score
from src.scoring.explainability import explain_candidate
from src.scoring.skill_gap import get_skill_gap

from src.semantic.similar_candidates import (
    find_similar_candidates
)
from src.semantic.recruiter_search import (
    build_search_index,
    recruiter_search
)
from src.scoring.hiring_recommendation import (
    get_hiring_recommendation
)
from src.recruiter.pipeline import (
    save_status,
    get_status,
    load_actions
)

# --------------------------------------------------
# ENV
# --------------------------------------------------

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(
    page_title="TalentMind",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 TalentMind")

st.markdown("""
### Enterprise Candidate Intelligence Platform

AI-powered candidate discovery, semantic ranking,
skill gap analysis and recruiter workflow automation.
""")

# --------------------------------------------------
# CACHE
# --------------------------------------------------

@st.cache_data
def get_candidates():

    return load_candidates(
        "data/raw/candidates.jsonl"
    )
@st.cache_resource
def initialize_faiss(candidates):

    build_search_index(
        candidates
    )

    return True

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("Recruiter Controls")

uploaded_jd = st.sidebar.file_uploader(
    "Upload Job Description",
    type=["txt"]
)

run_button = st.sidebar.button(
    "🚀 Rank Candidates"
)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

if run_button:

    if uploaded_jd is None:

        st.error(
            "Upload a Job Description first"
        )
        st.stop()

    jd = uploaded_jd.read().decode(
        "utf-8"
    )

    # ------------------------------------------
    # LOAD
    # ------------------------------------------

    with st.spinner(
        "Loading candidate database..."
    ):

        candidates = get_candidates()
    initialize_faiss(candidates)
    st.success(
    f"{len(candidates):,} Candidates Loaded"
)

    # ------------------------------------------
    # RULE RANK
    # ------------------------------------------

    with st.spinner(
        "Running rule engine..."
    ):

        ranked = sorted(
            candidates,
            key=calculate_final_score,
            reverse=True
        )

    # ------------------------------------------
    # SEMANTIC RANK
    # ------------------------------------------

    top_1000 = ranked[:1000]

    with st.spinner(
        "Running semantic matching..."
    ):

        results = []

        for candidate in top_1000:

            score = round(
                hybrid_score(
                    candidate,
                    jd
                ),
                2
            )
            if score >= 170:
                badge = "🟢 Strong Match"

            elif score >= 140:
                badge = "🟡 Good Match"

            else:
                badge = "🔴 Weak Match"

            results.append(
                (
                    candidate,
                    score
                )
            )

        results.sort(
            key=lambda x: x[1],
            reverse=True
        )

    st.success(
        "Ranking Complete"
    )

    # ==================================================
    # DASHBOARD
    # ==================================================

    st.header("📊 Dashboard")
    actions = load_actions()

    shortlisted = sum(
        1 for x in actions.values()
        if x == "Shortlisted"
    )

    interview = sum(
        1 for x in actions.values()
        if x == "Interview"
    )

    rejected = sum(
        1 for x in actions.values()
        if x == "Rejected"
    )

    hired = sum(
        1 for x in actions.values()
        if x == "Hired"
    )

    c1,c2,c3,c4,c5,c6 = st.columns(6)

    c1.metric("Candidates", len(candidates))
    c2.metric("Ranked", len(results))
    c3.metric("Shortlisted", shortlisted)
    c4.metric("Interview", interview)
    c5.metric("Rejected", rejected)
    c6.metric("Hired", hired)

    c1.metric(
        "Candidates",
        f"{len(candidates):,}"
    )

    c2.metric(
        "Ranked",
        f"{len(results):,}"
    )

    c3.metric(
        "Best Match",
        results[0][1]
    )

    c4.metric(
        "JD Length",
        len(jd)
    )

    st.divider()

    # ==================================================
    # RECRUITER SEARCH
    # ==================================================

    st.header("🔍 Recruiter Search")

    search_query = st.text_input(
        "Search Candidates",
        placeholder=
        "Machine Learning Engineer with RAG experience"
    )
    if search_query:

        search_results = recruiter_search(
            search_query,
            top_k=10
        )

        st.subheader(
            "Search Results"
        )

        for candidate, similarity in search_results:

            st.markdown(
                f"""
    ### #{rank} {candidate.profile.current_title}

    **Company:** {candidate.profile.current_company}

    **Experience:** {candidate.profile.years_of_experience} years

    **Similarity:** {round(similarity,3)}
    """
            )

            st.write(
                candidate.profile.summary[:300]
            )

            st.divider()

    # ==================================================
    # TOP CANDIDATES
    # ==================================================

    st.header(
        "🏆 Top Ranked Candidates"
    )

    for candidate, score in results[:20]:

        explanation = explain_candidate(
            candidate
        )

        with st.container():

            left, right = st.columns(
                [4, 1]
            )

            with left:

                st.markdown(
                    f"""
### {candidate.profile.current_title}

**Company:** {candidate.profile.current_company}

**Experience:** {candidate.profile.years_of_experience} years

**Location:** {candidate.profile.location}
"""
                )

            with right:

                st.metric(
                    "Score",
                    score
                )

            # --------------------------------------
            # Reasons
            # --------------------------------------

            if "reasons" in explanation:

                st.write(
                    "### Why Ranked High?"
                )

                for r in explanation[
                    "reasons"
                ]:

                    st.write(
                        "✅",
                        r
                    )

            status = get_status(
                candidate.candidate_id
            )

            st.caption(
                f"Pipeline Status: {status}"
            )

            # --------------------------------------
            # Profile
            # --------------------------------------

            with st.expander(
                "View Candidate"
            ):
                
                gap = get_skill_gap(
                    candidate,
                    jd
                )
                summary = generate_summary(
                candidate,
                explanation,
                gap
            )
                st.metric(
                    "Overall Match Score",
                    score
                )
            
                
                st.subheader(
                    "🤖 AI Recruiter Summary"
                )

                for point in summary:

                    st.info(
                    "\n\n".join(
                        [f"• {x}" for x in summary]
                    )
                )


                # ------------------
                # Skills
                # ------------------

                st.subheader(
                    "Skills"
                )

                skills = [
                    s.name
                    for s in candidate.skills
                ]

                st.write(
                    ", ".join(skills)
                )

                # ------------------
                # Gap Analysis
                # ------------------
              

                st.subheader(
                    "JD Gap Analysis"
                )

                a, b = st.columns(2)

                with a:

                    st.success(
                        f"Matched Skills ({len(gap['matched'])})"
                    )

                    for skill in gap[
                        "matched"
                    ]:

                        st.write(
                            "✅",
                            skill
                        )

                with b:

                    st.error(
                        f"Missing Skills ({len(gap['missing'])})"
                    )

                    for skill in gap[
                        "missing"
                    ]:

                        st.write(
                            "❌",
                            skill
                        )

                st.progress(
                    gap[
                        "match_percent"
                    ] / 100
                )

                st.write(
                    f"Skill Match: {gap['match_percent']}%"
                )

                st.subheader(
                    "Professional Summary"
                )

                st.write(
                    candidate.profile.summary
                )

                recommendation, reason = (
                    get_hiring_recommendation(
                        score,
                        gap["match_percent"],
                        explanation.get(
                            "red_flag_penalty",
                            0
                        )
                    )
                )

                st.subheader(
                    "🎯 Hiring Recommendation"
                )

                if recommendation == "Strong Hire":

                    st.success(
                        "🟢 Strong Hire"
                    )

                elif recommendation == "Interview":

                    st.info(
                        "🔵 Interview"
                    )

                elif recommendation == "Consider":

                    st.warning(
                        "🟡 Consider"
                    )

                else:

                    st.error(
                        "🔴 Reject"
                    )

                st.write(reason)

                st.subheader(
                    "Recruiter Actions"
                )

                c1,c2,c3,c4 = st.columns(4)

                with c1:

                    if st.button(
                        "⭐ Shortlist",
                        key=f"short_{candidate.candidate_id}"
                    ):

                        save_status(
                            candidate.candidate_id,
                            "Shortlisted"
                        )

                with c2:

                    if st.button(
                        "📞 Interview",
                        key=f"interview_{candidate.candidate_id}"
                    ):

                        save_status(
                            candidate.candidate_id,
                            "Interview"
                        )
                    st.markdown(
                        f"### {badge}"
                    )

                    st.progress(
                    min(score / 200, 1.0)
                )

                with c3:

                    if st.button(
                        "❌ Reject",
                        key=f"reject_{candidate.candidate_id}"
                    ):

                        save_status(
                            candidate.candidate_id,
                            "Rejected"
                        )

                with c4:

                    if st.button(
                    "🎉 Hire",
                    key=f"hire_{candidate.candidate_id}"
                ):

                        save_status(
                            candidate.candidate_id,
                            "Hired"
                        )

                current_status = get_status(
                    candidate.candidate_id
                )

                st.info(
                    f"Current Status: {current_status}"
                )

                # ------------------
                # Similar Profiles
                # ------------------

                try:

                    st.subheader(
                        "Similar Candidates"
                    )

                    sims = (
                        find_similar_candidates(
                            candidate,
                            top_k=3
                        )
                    )

                    for sim in sims:

                        if sim.candidate_id == candidate.candidate_id:
                            continue

                        st.write(
                            f"🔹 {sim.profile.current_title} | "
                            f"{sim.profile.current_company}"
                        )

                except:
                    pass

                # ------------------
                # Career
                # ------------------

                st.subheader(
                    "Career History"
                )

                for job in candidate.career_history:

                    st.markdown(
                        f"**{job.title}**"
                    )

                    st.write(
                        job.company
                    )

                    st.write(
                        job.description
                    )

                    st.divider()

                st.subheader(
                    "Explainability"
                )

                st.json(
                    explanation
                )

        st.divider()

    # ==================================================
    # EXPORT
    # ==================================================

    st.header("📥 Export")

    export_data = []

    for candidate, score in results[:100]:

        export_data.append({

            "candidate_id":
                candidate.candidate_id,

            "title":
                candidate.profile.current_title,

            "company":
                candidate.profile.current_company,

            "experience":
                candidate.profile.years_of_experience,

            "score":
                score
        })

    df = pd.DataFrame(
        export_data
    )

    st.dataframe(
        df.head(20),
        use_container_width=True
    )

    csv = df.to_csv(
        index=False
    )

    st.download_button(
        "Download CSV",
        csv,
        "top_100_candidates.csv",
        "text/csv"
    )

    # JSON Export

    with open(
        "outputs/top_100_candidates.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            export_data,
            f,
            indent=4
        )

    st.success(
        "Exports Generated"
    )