"""AI Recruiter Copilot page rendering test (Module 14).

Renders the copilot page via an inline Streamlit script (AppTest) with a synthetic
repository and an isolated temp AI cache/telemetry dir, then drives one message
through the chat to verify the end-to-end UI flow works offline.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import faiss  # noqa: F401  (faiss-before-torch load order)
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1].as_posix()
_TMP = tempfile.mkdtemp(prefix="talentmind_copilot_ui_")

_SCRIPT = f"""
import os
os.environ["TALENTMIND_AI_CACHE_DIR"] = r"{_TMP}/cache"
os.environ["TALENTMIND_AI_TELEMETRY_DIR"] = r"{_TMP}/logs"

import faiss  # noqa: F401
import sys
sys.path.insert(0, r"{ROOT}")
sys.path.insert(0, r"{ROOT}/tests")

from conftest import make_candidate
from src.ai.tools.provider import InMemoryCandidateRepository
from src.ui.copilot_page import render_copilot


def _factory():
    return InMemoryCandidateRepository([
        make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer"),
        make_candidate(candidate_id="CAND_0000002", title="Backend Engineer",
                       skills=["Java", "Spring"], years=4.0),
    ])


render_copilot(_factory, jd="python machine learning llm aws docker")
"""


def test_copilot_page_renders():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    titles = " ".join(t.value for t in at.title)
    assert "Recruiter Copilot" in titles


def test_copilot_page_answers_a_message():
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.run()
    assert not at.exception
    assert at.chat_input, "chat input should be present"

    at.chat_input[0].set_value("Find machine learning engineers").run()
    assert not at.exception

    rendered = " ".join(md.value for md in at.markdown)
    # The assistant answer for a search names the top match.
    assert "Top matches" in rendered or "candidates" in rendered.lower()
