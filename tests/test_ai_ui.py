"""AI Hiring Analyst tab rendering test (Module 13).

Renders the AI tab via an inline Streamlit script (AppTest) with a synthetic
candidate, using an isolated temp cache/telemetry directory so the test never
touches the real ``data/ai_cache``. Verifies the on-demand generate flow works
end-to-end through the UI with the offline provider.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1].as_posix()
_TMP = tempfile.mkdtemp(prefix="talentmind_ai_ui_")

_SCRIPT = f"""
import os
os.environ["TALENTMIND_AI_CACHE_DIR"] = r"{_TMP}/cache"
os.environ["TALENTMIND_AI_TELEMETRY_DIR"] = r"{_TMP}/logs"

import faiss  # noqa: F401
import sys
sys.path.insert(0, r"{ROOT}")
sys.path.insert(0, r"{ROOT}/tests")

from src.ai.services import hiring_analyst_service as svc
svc.get_runner.cache_clear()  # rebuild the runner against the temp dirs

from conftest import make_candidate
from src.insights.builder import build_insights
from src.interview.planner import build_interview_plan
from src.ui.ai_analyst_tab import render_ai_analyst_tab

candidate = make_candidate(candidate_id="UITEST")
jd = "python machine learning llm aws docker"
insights = build_insights(candidate, jd, 150.0)
plan = build_interview_plan(insights)

render_ai_analyst_tab("UITEST", insights, plan, jd)
"""


def test_ai_tab_renders_and_generates():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception

    # Before generation: subheader present, generate button present.
    subheaders = " ".join(s.value for s in at.subheader)
    assert "AI Hiring Analyst" in subheaders

    generate = next((b for b in at.button if b.key == "ai_gen_UITEST"), None)
    assert generate is not None

    # On-demand generation via the offline provider.
    generate.click()
    at.run()
    assert not at.exception

    # After generation: an executive decision banner is rendered as a status box.
    rendered = " ".join([md.value for md in at.markdown] + [s.value for s in at.subheader])
    assert "Executive Summary" in rendered
