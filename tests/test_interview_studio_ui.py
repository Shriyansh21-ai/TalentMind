"""Streamlit AppTest for the Interview Studio dashboard (Module 17).

Renders the interview-studio workspace in isolation with a synthetic candidate
(no dataset / FAISS / provider) so it is fast, offline and deterministic while
proving the workspace boots, builds the plan, renders every tab and the visual
dashboard.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.interview_studio_tab import render_interview_studio

candidate = make_candidate(candidate_id="CAND_IS_1", title="Senior ML Engineer")
JD = '''Senior Machine Learning Engineer
What you'll do
- Design and own scalable ML systems in production
Requirements
- 8+ years experience
- Python, PyTorch, AWS
'''
render_interview_studio(candidate, jd=JD)
"""


def test_interview_studio_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Interview Studio dashboard raised: {at.exception}"


def test_interview_studio_dashboard_renders_headline():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Interview Studio" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Role Path" in label for label in metric_labels)
    assert any("Readiness" in label for label in metric_labels)
