"""Executive Hiring Report — the Executive Decision Layer (Phase 4 / Milestone 4).

Transforms every structured intelligence output TalentMind already produced
(committee, resume, JD, candidate intelligence, timeline, risk, interview,
recommendation, pipeline) into boardroom-grade executive reports. It adds **no
hiring logic and no ranking** — it consumes existing outputs and renders them.

Importing the package auto-registers the :class:`ExecutiveHiringReportAgent` with
the AI Platform, the deterministic composer registry and the Multi-Agent
Orchestration registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.executive_report.agent import (
    ExecutiveHiringReportAgent,
    ExecutiveReportInput,
    executive_report_agent,
)
from src.ai.agents.executive_report.builder import (
    ExecutiveReportBuilder,
    executive_report_builder,
)
from src.ai.agents.executive_report.schemas import (
    ExecutiveHiringReport,
    ExecutiveNarrative,
)

__all__ = [
    "ExecutiveHiringReportAgent",
    "ExecutiveReportInput",
    "executive_report_agent",
    "ExecutiveReportBuilder",
    "executive_report_builder",
    "ExecutiveHiringReport",
    "ExecutiveNarrative",
]
