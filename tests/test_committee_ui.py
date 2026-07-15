"""Streamlit AppTest for the AI Hiring Committee dashboard (Module 17).

Renders the committee dashboard in isolation with a synthetic candidate (no
dataset / FAISS / provider) so it is fast, offline and deterministic while
proving the workspace boots, runs the committee and renders the decision.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.committee_tab import render_committee

candidate = make_candidate(candidate_id="CAND_CM_1", title="Senior ML Engineer")
JD = '''Senior Machine Learning Engineer
What you'll do
- Design and own scalable ML systems in production
Requirements
- 8+ years experience
- Python, PyTorch, AWS
'''
render_committee(candidate, jd=JD, mode="balanced")
"""


def test_committee_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=90)
    at.run()
    assert not at.exception, f"Committee dashboard raised: {at.exception}"


def test_committee_dashboard_renders_decision():
    at = AppTest.from_string(_SCRIPT, default_timeout=90)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Hiring Committee" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Recommendation" in label for label in metric_labels)
    assert any("Consensus" in label for label in metric_labels)
