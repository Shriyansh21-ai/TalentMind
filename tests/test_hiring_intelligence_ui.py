"""Streamlit AppTest for the Hiring Intelligence dashboard (Module 16).

Renders the workforce-intelligence workspace in isolation with a synthetic cohort
(no dataset / FAISS / provider) so it is fast, offline and deterministic while
proving the workspace boots, aggregates the cohort (analytics-unavailable path)
and renders every tab and the dashboard.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.hiring_intelligence_tab import render_hiring_intelligence

cohort = [
    make_candidate(candidate_id="C1", title="Senior ML Engineer", years=9),
    make_candidate(candidate_id="C2", title="Backend Engineer", years=5),
    make_candidate(candidate_id="C3", title="Data Scientist", years=3),
    make_candidate(candidate_id="C4", title="Engineering Manager", years=12),
]
render_hiring_intelligence(cohort, jd="Senior ML Engineer", generated_on="2026-07-16")
"""


def test_hiring_intelligence_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Hiring Intelligence dashboard raised: {at.exception}"


def test_hiring_intelligence_dashboard_renders_headline():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Workforce Analytics" in s or "Hiring Intelligence" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Cohort" in label for label in metric_labels)
    assert any("Hiring Health" in label for label in metric_labels)
