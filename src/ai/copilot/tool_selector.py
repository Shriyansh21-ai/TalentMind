"""Intent → tool selection policy.

A declarative mapping (not a branchy if-else) from each :class:`Intent` to the
minimal set of tools needed to answer it. This is the heart of Module 5: the
copilot never runs every tool. Adding an intent or retargeting one is a one-line
data change; new tools plug in by name.
"""

from __future__ import annotations

from typing import Dict, List

from src.ai.copilot.models import Intent

# Minimal tool set per intent. Order matters (search before candidate tools).
INTENT_TOOLS: Dict[Intent, List[str]] = {
    Intent.SEARCH_CANDIDATE: ["faiss_search"],
    Intent.SKILL_SEARCH: ["faiss_search", "skill_gap"],
    Intent.COMPARE_CANDIDATES: ["comparison", "risk", "timeline"],
    Intent.EXPLAIN_RANKING: ["explainability", "skill_gap"],
    Intent.GENERATE_HIRING_SUMMARY: ["candidate_intelligence", "recommendation", "risk"],
    Intent.ANALYZE_CANDIDATE: [
        "candidate_intelligence",
        "timeline",
        "risk",
        "recommendation",
    ],
    Intent.GENERATE_INTERVIEW_PLAN: ["interview", "skill_gap"],
    Intent.PIPELINE_QUESTION: ["pipeline"],
    Intent.DASHBOARD_QUESTION: ["dashboard"],
    Intent.RECOMMENDATION_QUESTION: ["recommendation", "candidate_intelligence"],
    Intent.GENERAL_HIRING_QUESTION: [],
}


def select_tools(intent: Intent) -> List[str]:
    """Return the ordered tool names for ``intent`` (empty for general Q&A)."""
    return list(INTENT_TOOLS.get(intent, []))
