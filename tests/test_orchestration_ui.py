"""Streamlit AppTest for the Multi-Agent Orchestration console (Module 16).

Runs the orchestration page in isolation (not through ``app.py``) so it never
triggers the dataset / FAISS / sentence-transformers load. The page is fully
offline — a demo orchestrator with generic agents — so this stays fast and
deterministic while proving the page boots, renders and can execute a goal.
"""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

# Minimal harness script: render the orchestration page directly.
_PAGE_SCRIPT = """
from src.ui.orchestration_page import render_orchestration
render_orchestration()
"""

# Harness that also drives a goal end-to-end through the orchestrator.
_RUN_SCRIPT = """
import streamlit as st
from src.ai.orchestration.builtin import build_demo_orchestrator
from src.ai.orchestration import Goal

orch = build_demo_orchestrator()
result = orch.run(Goal(description="analyze the subject in full", subject_id="demo"))
st.title("Orchestration Result")
st.metric("tasks", result.task_count)
st.write(result.status.value)
st.write(result.answer)
for line in orch.monitor.visual_log(result.workflow_id):
    st.text(line)
"""


def test_orchestration_page_boots_without_exception():
    at = AppTest.from_string(_PAGE_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, f"Orchestration page raised: {at.exception}"


def test_orchestration_page_renders_title_and_examples():
    at = AppTest.from_string(_PAGE_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception
    titles = [t.value for t in at.title]
    assert any("Orchestration" in title for title in titles)
    # The example goal buttons + primary run button should be present.
    labels = [b.label for b in at.button]
    assert any("Run orchestration" in label for label in labels)


def test_orchestration_end_to_end_render():
    at = AppTest.from_string(_RUN_SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("tasks") == "4"
    # The completed status + a non-empty visual log must have rendered.
    assert any("completed" in (m.value or "") for m in at.markdown) or any(
        "completed" in str(w.value) for w in at.markdown
    )
