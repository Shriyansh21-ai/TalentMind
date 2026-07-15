"""Streamlit AppTest for the Resume Intelligence dashboard (Module 18).

Renders the dashboard in isolation with a synthetic candidate (no dataset /
FAISS / provider) so it is fast, offline and deterministic while proving the tab
boots, runs the agent and renders the analysis.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.resume_intelligence_tab import render_resume_intelligence

candidate = make_candidate(candidate_id="CAND_UI_1")
render_resume_intelligence(candidate, jd="python aws kubernetes")
"""


def test_resume_intelligence_tab_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, f"Resume Intelligence tab raised: {at.exception}"


def test_resume_intelligence_tab_renders_dashboard():
    at = AppTest.from_string(_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception
    # Overall quality metric + subheader must render.
    subheaders = [s.value for s in at.subheader]
    assert any("Resume Intelligence" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Overall Resume Quality" in label for label in metric_labels)
