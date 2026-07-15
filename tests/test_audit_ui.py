"""Streamlit AppTest for the Hiring Audit dashboard (Module 15).

Renders the audit workspace in isolation with a synthetic candidate (no dataset /
FAISS / archive) so it is fast, offline and deterministic while proving the
workspace boots, reconstructs the journey (archive-unavailable path) and renders
every tab and the dashboard.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.audit_tab import render_audit

candidate = make_candidate(candidate_id="CAND_AU_1", title="Senior ML Engineer")
JD = '''Senior Machine Learning Engineer
- Design and own scalable ML systems in production
Requirements: 8+ years, Python, PyTorch, AWS
'''
render_audit(candidate, jd=JD, generated_on="2026-07-16")
"""


def test_audit_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Audit dashboard raised: {at.exception}"


def test_audit_dashboard_renders_headline():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Audit" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Agents" in label for label in metric_labels)
    assert any("Audit Readiness" in label for label in metric_labels)
