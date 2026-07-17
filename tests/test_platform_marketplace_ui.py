"""Integration Marketplace workspace rendering test (Module 11 · Module 16).

Renders the enterprise integration console via an inline Streamlit script
(AppTest) against the deterministic, offline demo integration platform. Verifies
the page renders without exception and surfaces the required sections.
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

from src.ui.integration_marketplace import render_integration_marketplace

render_integration_marketplace()
"""


def test_integration_marketplace_renders():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception

    titles = " ".join(t.value for t in at.title)
    assert "Integration Marketplace" in titles

    # KPI header metrics.
    labels = {m.label for m in at.metric}
    assert {"Available providers", "Installed", "Connected"} <= labels

    # Required sections present as subheaders across the tabs.
    subheaders = " ".join(s.value for s in at.subheader)
    for expected in [
        "Available Providers",
        "Installed Integrations",
        "Webhooks",
        "Synchronization",
        "Enterprise Event Bus",
        "Developer SDK Foundation",
    ]:
        assert expected in subheaders, expected
