"""UI-rendering integration checks for the Enterprise Workspace (Module 10).

Drives each workspace UI surface through an inline Streamlit script (AppTest) with
two synthetic candidates, asserting nothing raises. This exercises the real
render code paths (dashboard charts, talent pools, smart filters, comparison,
interview plan) without loading the production dataset or the FAISS index.
"""

from __future__ import annotations

from pathlib import Path

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1].as_posix()

_SCRIPT = f"""
import faiss  # noqa: F401
import sys
sys.path.insert(0, r"{ROOT}")
sys.path.insert(0, r"{ROOT}/tests")

import streamlit as st
from conftest import make_candidate
from src.ui.helpers import get_insights
from src.ui import (
    analytics_dashboard,
    talent_pool_view,
    filters_panel,
    comparison_view,
    interview_tab,
)
from src.interview.planner import build_interview_plan

jd = "python machine learning llm aws docker rag"
cands = [
    make_candidate(candidate_id="A", title="Senior Machine Learning Engineer"),
    make_candidate(candidate_id="B", title="Backend Engineer",
                   skills=["Java", "Spring", "Microservices"], years=4.0),
]
insights = [get_insights(c, jd, 150.0) for c in cands]
states = {{}}

analytics_dashboard.render_enterprise_dashboard(cands, insights, states)
talent_pool_view.render_talent_pools(insights)
filters_panel.render_smart_filters(insights, states)

st.session_state["workspace_compare_ids"] = ["A", "B"]
candidate_by_id = {{c.candidate_id: c for c in cands}}
comparison_view.render_comparison_workspace(candidate_by_id, jd)

interview_tab.render_interview_tab(build_interview_plan(insights[0]))
"""


def test_workspace_surfaces_render_without_exception():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Workspace UI raised: {at.exception}"


def test_workspace_renders_expected_headers():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    rendered = " ".join(sh.value for sh in at.subheader)
    assert "Enterprise Analytics" in rendered
    assert "Talent Pools" in rendered
    assert "Smart Filters" in rendered
    assert "Candidate Comparison" in rendered
    assert "Interview Plan" in rendered
