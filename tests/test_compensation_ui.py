"""Streamlit AppTest for the Compensation Governance dashboard (Module 17).

Renders the compensation-governance workspace in isolation with a synthetic
candidate (no dataset / FAISS / provider) so it is fast, offline and deterministic
while proving the workspace boots, builds the report, renders every tab, the
dashboard and the exportable transparency audit trail.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.compensation_tab import render_compensation

candidate = make_candidate(candidate_id="CAND_CG_1", title="Senior ML Engineer")
JD = '''Senior Machine Learning Engineer
- Design and own scalable ML systems in production
Requirements: 8+ years, Python, PyTorch, AWS
'''
render_compensation(candidate, jd=JD, generated_on="2026-07-15")
"""


def test_compensation_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Compensation dashboard raised: {at.exception}"


def test_compensation_dashboard_renders_headline():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Compensation Governance" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Market Position" in label for label in metric_labels)
    assert any("Recommended Target" in label for label in metric_labels)
