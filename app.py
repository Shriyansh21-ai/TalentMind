# app.py
"""TalentMind — Enterprise Candidate Intelligence Platform.

Thin Streamlit orchestrator. It wires the (unchanged) scoring, semantic and
intelligence engines in ``src/`` to the presentation modules in ``src/ui/``:

    Load Data -> Rule Rank -> Semantic Rank -> Dashboard -> Search
             -> Candidate Cards -> Export

All ranking formulas, scoring, embeddings and recommendation logic live in
``src/`` and are invoked here without modification.
"""

import os

# NOTE: faiss must be imported before torch / sentence-transformers. On Windows
# the reverse OpenMP load order segfaults the process at import time. Importing
# faiss first here (the single entry point) guarantees a safe load order.
import faiss  # noqa: F401  (imported for load-order side effect only)

import streamlit as st

from src.ingestion.candidate_loader import load_candidates
from src.scoring.final_score import calculate_final_score
from src.scoring.hybrid_score import hybrid_score
from src.semantic.recruiter_search import build_search_index
from src.intelligence.jd_parser import parse_jd
from src.intelligence.jd_analyzer import analyze
from src.intelligence.dashboard import show_job_dashboard
from src.recruiter.pipeline import load_actions

from src.ui.sidebar import render_sidebar
from src.ui.dashboard import render_dashboard
from src.ui.recruiter_search import render_recruiter_search
from src.ui.candidate_card import render_candidate_card
from src.ui.export import render_export

# --------------------------------------------------
# ENV
# --------------------------------------------------

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

CANDIDATES_PATH = "data/raw/candidates.jsonl"
SEMANTIC_POOL_SIZE = 1000
TOP_CANDIDATES = 20

# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(
    page_title="TalentMind",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 TalentMind")

st.markdown(
    """
### Enterprise Candidate Intelligence Platform

AI-powered candidate discovery, semantic ranking,
skill gap analysis and recruiter workflow automation.
"""
)


# --------------------------------------------------
# CACHE
# --------------------------------------------------


@st.cache_data
def get_candidates():
    """Load and cache the candidate database (parsed once per session)."""
    return load_candidates(CANDIDATES_PATH)


@st.cache_resource
def initialize_faiss(candidates):
    """Build the FAISS search index once and cache it for the session."""
    build_search_index(candidates)
    return True


# --------------------------------------------------
# ORCHESTRATION
# --------------------------------------------------


def main() -> None:
    """Drive the end-to-end recruiter pipeline for a single run."""
    uploaded_jd, run_button = render_sidebar()

    if not run_button:
        return

    if uploaded_jd is None:
        st.error("Upload a Job Description first")
        st.stop()

    jd = uploaded_jd.read().decode("utf-8")

    if not jd.strip():
        st.error("The uploaded Job Description is empty")
        st.stop()

    # ---- Job Intelligence -------------------------------------------------
    job_profile = analyze(parse_jd(jd))
    show_job_dashboard(job_profile)

    # ---- Load candidates --------------------------------------------------
    with st.spinner("Loading candidate database..."):
        candidates = get_candidates()

    if not candidates:
        st.error("No candidates found in the database")
        st.stop()

    initialize_faiss(candidates)
    st.success(f"{len(candidates):,} Candidates Loaded")

    # ---- Rule-based ranking ----------------------------------------------
    with st.spinner("Running rule engine..."):
        ranked = sorted(candidates, key=calculate_final_score, reverse=True)

    # ---- Semantic (hybrid) ranking ---------------------------------------
    with st.spinner("Running semantic matching..."):
        results = [
            (candidate, round(hybrid_score(candidate, job_profile), 2))
            for candidate in ranked[:SEMANTIC_POOL_SIZE]
        ]
        results.sort(key=lambda x: x[1], reverse=True)

    st.success("Ranking Complete")

    if not results:
        st.warning("No candidates could be ranked for this job description.")
        return

    # ---- Render ----------------------------------------------------------
    actions = load_actions()
    render_dashboard(candidates, results, jd, actions)

    render_recruiter_search()

    st.header("🏆 Top Ranked Candidates")
    for rank, (candidate, score) in enumerate(results[:TOP_CANDIDATES], start=1):
        render_candidate_card(rank, candidate, score, jd)

    render_export(results)


if __name__ == "__main__":
    main()

