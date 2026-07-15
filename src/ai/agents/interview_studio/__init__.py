"""Enterprise AI Interview Studio (Phase 4 / Milestone 5).

The final operational layer of TalentMind's hiring lifecycle. It transforms every
structured intelligence output TalentMind already produced (resume, JD,
committee, candidate intelligence, timeline, risk, the deterministic interview
plan and the hiring recommendation) into a complete, recruiter-ready interview
package: an interview strategy, an adaptive question flow, evaluation rubrics,
interviewer guides, feedback templates and a decision matrix. It adds **no hiring
logic and no ranking** — it consumes existing outputs and restates them for the
interview panel.

Importing the package auto-registers the :class:`InterviewStudioAgent` with the
AI Platform, the deterministic composer registry and the Multi-Agent
Orchestration registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.interview_studio.agent import (
    InterviewStudioAgent,
    InterviewStudioInput,
    build_interview_evidence,
    interview_studio_agent,
)
from src.ai.agents.interview_studio.report import (
    InterviewStudioEngine,
    interview_studio_engine,
)
from src.ai.agents.interview_studio.schemas import (
    InterviewStudioNarrative,
    InterviewStudioReport,
)

__all__ = [
    "InterviewStudioAgent",
    "InterviewStudioInput",
    "build_interview_evidence",
    "interview_studio_agent",
    "InterviewStudioEngine",
    "interview_studio_engine",
    "InterviewStudioNarrative",
    "InterviewStudioReport",
]
