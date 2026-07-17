"""Streamlit AppTest for the JD Intelligence dashboard (Module 18).

Renders the dashboard in isolation with a sample JD (no dataset / FAISS /
provider) so it is fast, offline and deterministic while proving the tab boots,
runs the agent and renders the analysis.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

_SCRIPT = """
from src.ui.jd_intelligence_tab import render_jd_intelligence

JD = '''Senior Machine Learning Engineer
Department: AI Platform
Location: Remote

What you'll do
- Design and own scalable ML systems in production
- Lead and mentor a team

Requirements
- 8+ years experience
- Python, PyTorch, AWS, Kubernetes
'''
render_jd_intelligence(JD, jd_id="JD_UI_1")
"""


def test_jd_intelligence_tab_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, f"JD Intelligence tab raised: {at.exception}"


def test_jd_intelligence_tab_renders_dashboard():
    at = AppTest.from_string(_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("JD Intelligence" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Overall JD Quality" in label for label in metric_labels)
