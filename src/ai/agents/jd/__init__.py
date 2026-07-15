"""JD Intelligence Agent (Phase 4 / Milestone 2).

The second specialized enterprise agent on TalentMind's AI + orchestration
platforms. :class:`JDAnalystAgent` deeply understands a Job Description — its
role level, technical shape, hiring intent, organizational context, requirement
hierarchy, market posture, quality and risks — thinking like a senior recruiter,
hiring manager, engineering director, org designer, technical lead and workforce
planner at once. It is **not** a keyword parser and it never ranks candidates.

Importing this package auto-registers the agent with:

* the AI Platform agent registry (``src.ai.core.registry.registry``),
* the deterministic composer registry (offline reasoning), and
* the Multi-Agent Orchestration registry (via a :class:`RunnerAgent` adapter).

The Recruiter Copilot discovers the accompanying ``jd_analysis`` tool
automatically through the tool registry — no manual routing.
"""

from __future__ import annotations

from src.ai.agents.jd.agent import (
    JDAnalystAgent,
    JDAnalystInput,
    jd_analyst_agent,
)
from src.ai.agents.jd.schemas import JDAnalysis

__all__ = [
    "JDAnalystAgent",
    "JDAnalystInput",
    "jd_analyst_agent",
    "JDAnalysis",
]
