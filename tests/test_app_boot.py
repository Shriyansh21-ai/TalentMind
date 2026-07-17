"""Streamlit AppTest boot check (Module 10).

Verifies the app boots end-to-end through Streamlit's own test harness without
raising, and that the sidebar controls render. Because ``main()`` returns early
until the recruiter clicks *Rank Candidates*, running the app renders only the
title + sidebar + intro — it does **not** load the 487 MB dataset or build the
FAISS index, so this stays fast while still exercising every top-level import
(including the faiss-before-torch load order) and the module wiring.
"""

from __future__ import annotations

from pathlib import Path

import faiss  # noqa: F401  (preserve faiss-before-torch load order in-process)
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_boots_without_exception():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception, f"App raised on boot: {at.exception}"


def test_app_renders_title_and_sidebar():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception

    titles = [t.value for t in at.title]
    assert any("TalentMind" in title for title in titles)

    # The sidebar rank button must be present (the primary recruiter control).
    button_labels = [b.label for b in at.button]
    assert any("Rank Candidates" in label for label in button_labels)


def test_app_requires_jd_before_ranking():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    # Click "Rank Candidates" with no JD uploaded -> app should error gracefully,
    # not crash. This exercises the guard path without loading candidates.
    for button in at.button:
        if "Rank Candidates" in button.label:
            button.click()
            break
    at.run()
    assert not at.exception
    assert any("Upload a Job Description" in e.value for e in at.error)
