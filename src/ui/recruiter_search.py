"""Free-text semantic recruiter search UI for TalentMind."""

import streamlit as st

from src.semantic.recruiter_search import recruiter_search


def render_recruiter_search() -> None:
    """Render the recruiter search box and its results.

    Behaviour matches the original inline block: a text query is run through
    the FAISS-backed ``recruiter_search`` (``top_k=10``) and each hit is shown
    with title, company, location, similarity and a summary preview. Empty
    queries and empty result sets are handled gracefully.
    """
    st.header("🔍 Recruiter Search")

    search_query = st.text_input(
        "Search Candidates",
        placeholder="Machine Learning Engineer with RAG experience",
    )

    if not search_query:
        return

    try:
        search_results = recruiter_search(search_query, top_k=10)
    except Exception:
        st.warning("Search is unavailable — the search index is not ready.")
        return

    if not search_results:
        st.info("No matching candidates found.")
        return

    st.subheader("Search Results")

    for rank, (candidate, similarity) in enumerate(search_results, start=1):
        st.markdown(
            f"""
### #{rank} {candidate.profile.current_title}

 {candidate.profile.current_company}

 {candidate.profile.location}

 Similarity Score: {round(similarity, 3)}
"""
        )

        st.write(candidate.profile.summary[:300])

        st.divider()
