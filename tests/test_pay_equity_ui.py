"""Streamlit AppTest for the Pay Equity Guardian dashboard (Module 15).

Renders the pay-equity workspace in isolation with a synthetic candidate (no
dataset / FAISS / provider) so it is fast, offline and deterministic while proving
the workspace boots, builds the report (data-unavailable path) and renders every
tab and the dashboard.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

_SCRIPT = """
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
from conftest import make_candidate
from src.ui.pay_equity_tab import render_pay_equity

candidate = make_candidate(candidate_id="CAND_PE_1", title="Senior ML Engineer")
JD = '''Senior Machine Learning Engineer
- Design and own scalable ML systems in production
Requirements: 8+ years, Python, PyTorch, AWS
'''
render_pay_equity(candidate, jd=JD, generated_on="2026-07-15")
"""


def test_pay_equity_dashboard_boots():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception, f"Pay Equity dashboard raised: {at.exception}"


def test_pay_equity_dashboard_renders_headline():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    subheaders = [s.value for s in at.subheader]
    assert any("Pay Equity Guardian" in s for s in subheaders)
    metric_labels = [m.label for m in at.metric]
    assert any("Equity Risk" in label for label in metric_labels)
    assert any("Compression" in label for label in metric_labels)
