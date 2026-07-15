"""Streamlit AppTest for the Executive Hiring Report dashboard (Module 18).

Renders the executive-report workspace in isolation with a synthetic candidate
(no dataset / FAISS / provider) so it is fast, offline and deterministic while
proving the workspace boots, builds the report, renders the visuals and offers
the exports.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.executive_report_tab import render_executive_report

candidate = make_candidate(candidate_id="CAND_ER_1", title="Senior ML Engineer")
JD = '''Senior Machine Learning Engineer
What you'll do
- Design and own scalable ML systems in production
Requirements
- 8+ years experience
- Python, PyTorch, AWS
'''
render_executive_report(candidate, jd=JD, template="executive")
"""


def test_executive_report_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Executive report dashboard raised: {at.exception}"


def test_executive_report_dashboard_renders_headline():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Executive Hiring Report" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Recommendation" in label for label in metric_labels)
    assert any("Action" in label for label in metric_labels)
