"""Platform Administration workspace rendering test (Module 13).

Renders the enterprise admin console via an inline Streamlit script (AppTest)
against the deterministic, offline demo platform. Verifies the page renders
without exception and surfaces the required operational sections.
"""

from __future__ import annotations

from pathlib import Path

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1].as_posix()

_SCRIPT = f"""
import faiss  # noqa: F401
import sys
sys.path.insert(0, r"{ROOT}")

from src.ui.platform_admin import render_platform_admin

render_platform_admin()
"""


def test_platform_admin_renders():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception

    titles = " ".join(t.value for t in at.title)
    assert "Platform Administration" in titles

    # KPI header metrics.
    labels = {m.label for m in at.metric}
    assert {"Organizations", "Tenants", "Users", "Audit events"} <= labels

    # Every required operational section is present as a subheader.
    subheaders = " ".join(s.value for s in at.subheader)
    for expected in [
        "System Status",
        "Organizations",
        "Users",
        "Subscriptions",
        "Licensing",
        "Configuration",
        "Audit Events",
    ]:
        assert expected in subheaders, expected
