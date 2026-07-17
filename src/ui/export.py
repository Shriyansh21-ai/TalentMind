"""Candidate export UI for TalentMind (CSV download + JSON file).

Behaviour matches the original inline export block: a preview table of the top
ranked candidates, a CSV download button, and a JSON file written to
``outputs/top_100_candidates.json`` with the same field set.
"""

import json
import os

import pandas as pd
import streamlit as st

from src.models.candidates import Candidate

OUTPUT_JSON_PATH = "outputs/top_100_candidates.json"
EXPORT_LIMIT = 100
PREVIEW_ROWS = 20


def render_export(results: list[tuple[Candidate, float]]) -> None:
    """Render the export section for the top ranked candidates.

    Args:
        results: Ranked ``(candidate, score)`` tuples (highest first).
    """
    st.header("📥 Export")

    if not results:
        st.info("No ranked candidates to export.")
        return

    export_data = [
        {
            "candidate_id": candidate.candidate_id,
            "title": candidate.profile.current_title,
            "company": candidate.profile.current_company,
            "experience": candidate.profile.years_of_experience,
            "score": score,
        }
        for candidate, score in results[:EXPORT_LIMIT]
    ]

    df = pd.DataFrame(export_data)

    st.dataframe(df.head(PREVIEW_ROWS), use_container_width=True)

    csv = df.to_csv(index=False)
    st.download_button(
        "Download CSV",
        csv,
        "top_100_candidates.csv",
        "text/csv",
    )

    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=4)

    st.success("Exports Generated")
