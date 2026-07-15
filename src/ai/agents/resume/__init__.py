"""Resume Intelligence Agent (Phase 4 / Milestone 1).

The first specialized enterprise agent on the TalentMind AI + orchestration
platforms. :class:`ResumeAnalystAgent` performs recruiter-grade resume
intelligence — thinking like a senior recruiter, hiring manager, resume
reviewer, career coach and ATS expert at once — **without** ranking candidates
and **without** touching any existing engine.

Importing this package auto-registers the agent with:

* the AI Platform agent registry (``src.ai.core.registry.registry``),
* the Multi-Agent Orchestration registry (``orchestration_registry``, via a
  :class:`RunnerAgent` adapter), and
* the deterministic composer registry (offline reasoning).

The Recruiter Copilot discovers the accompanying ``resume_analysis`` tool
automatically through the tool registry — no manual routing.
"""

from __future__ import annotations

from src.ai.agents.resume.agent import (
    ResumeAnalystAgent,
    ResumeAnalystInput,
    resume_analyst_agent,
)
from src.ai.agents.resume.schemas import ResumeAnalysis

__all__ = [
    "ResumeAnalystAgent",
    "ResumeAnalystInput",
    "resume_analyst_agent",
    "ResumeAnalysis",
]
