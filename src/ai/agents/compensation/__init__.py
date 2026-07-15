"""Enterprise Compensation Governance System (Phase 5 / Milestone 1).

NOT a salary-prediction engine. It explains, justifies, documents and governs a
compensation recommendation using evidence from TalentMind's existing AI
ecosystem so that HR, Finance, Legal, hiring managers and executives can
confidently approve it. It adds no ranking and no hiring logic — it consumes
existing outputs and fabricates no salary, payroll or market data.

Importing the package auto-registers the :class:`CompensationGovernanceAgent`
with the AI Platform, the deterministic composer registry and the Multi-Agent
Orchestration registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.compensation.agent import (
    CompensationGovernanceAgent,
    CompensationInput,
    build_compensation_evidence,
    compensation_agent,
)
from src.ai.agents.compensation.governance import (
    CompensationGovernanceEngine,
    compensation_governance_engine,
)
from src.ai.agents.compensation.internal_equity import (
    CompensationDataProvider,
    NullCompensationDataProvider,
)
from src.ai.agents.compensation.schemas import (
    CompensationNarrative,
    CompensationReport,
)

__all__ = [
    "CompensationGovernanceAgent",
    "CompensationInput",
    "build_compensation_evidence",
    "compensation_agent",
    "CompensationGovernanceEngine",
    "compensation_governance_engine",
    "CompensationDataProvider",
    "NullCompensationDataProvider",
    "CompensationNarrative",
    "CompensationReport",
]
