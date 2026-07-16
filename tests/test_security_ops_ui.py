"""Security & Operations Center rendering test (Module 10 · Module 15).

Renders the enterprise security console via an inline Streamlit script (AppTest)
against the deterministic, offline demo security platform. Verifies the page
renders without exception and surfaces the required sections.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1].as_posix()

_SCRIPT = f"""
import faiss  # noqa: F401
import sys
sys.path.insert(0, r"{ROOT}")

from src.ui.security_operations import render_security_operations

render_security_operations()
"""


def test_security_operations_renders():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception

    titles = " ".join(t.value for t in at.title)
    assert "Security & Operations Center" in titles

    labels = {m.label for m in at.metric}
    assert {"Identities", "Audit entries", "Active alerts", "Threat events"} <= labels

    subheaders = " ".join(s.value for s in at.subheader)
    for expected in [
        "System Overview",
        "Audit Timeline",
        "Alerts",
        "Threat Events",
        "Policy & Governance",
        "Compliance Status",
        "Incidents",
    ]:
        assert expected in subheaders, expected
