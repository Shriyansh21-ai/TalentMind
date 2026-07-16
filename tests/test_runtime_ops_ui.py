"""Runtime Operations workspace rendering test (Module 10 · Module 16).

Renders the enterprise runtime console via an inline Streamlit script (AppTest)
against the deterministic, offline demo runtime. Verifies the page renders
without exception and surfaces the required operational sections.
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

from src.ui.runtime_operations import render_runtime_operations

render_runtime_operations()
"""


def test_runtime_operations_renders():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception

    titles = " ".join(t.value for t in at.title)
    assert "Runtime Operations" in titles

    labels = {m.label for m in at.metric}
    assert {"Workers", "Queue depth", "Running", "Succeeded", "Failed"} <= labels

    subheaders = " ".join(s.value for s in at.subheader)
    for expected in [
        "Platform Health",
        "Workers",
        "Queue",
        "Jobs",
        "Cache",
        "Performance",
        "Resource Utilization",
        "Circuit Breakers",
        "Runtime Events",
    ]:
        assert expected in subheaders, expected
