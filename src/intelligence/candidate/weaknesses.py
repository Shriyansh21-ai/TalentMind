"""Candidate weakness detection.

NOTE: This module previously contained a copy-paste of ``strengths.py`` (it
defined a function named ``strengths``), which broke
``engine.py``'s ``from .weaknesses import weaknesses`` import. The rules below
were drafted to fill in the missing ``weaknesses`` function and mirror the
heuristic style of ``strengths.py``. Review/adjust the thresholds and phrasing
to match your intended hiring criteria.
"""

from typing import List


def weaknesses(candidate) -> List[str]:
    """Return a list of areas to validate for a candidate.

    Heuristics mirror ``strengths.py`` (skill presence + experience), inverted
    to surface gaps. Adjust freely — this is presentation-tier signal only and
    does not feed any score.
    """
    weaknesses: List[str] = []

    skills = {s.name.lower() for s in candidate.skills}

    if "python" not in skills:
        weaknesses.append("No demonstrated Python expertise")

    if "llm" not in skills:
        weaknesses.append("Limited production LLM experience")

    if "rag" not in skills:
        weaknesses.append("No Retrieval-Augmented systems experience")

    if candidate.profile.years_of_experience < 2:
        weaknesses.append("Limited overall experience")

    if len(skills) < 3:
        weaknesses.append("Narrow skill breadth")

    return weaknesses
