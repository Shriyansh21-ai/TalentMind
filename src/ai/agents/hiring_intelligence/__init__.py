"""Enterprise Workforce Hiring Intelligence System (Phase 5 / Milestone 5).

The Hiring Intelligence Agent aggregates the platform's existing hiring
intelligence into strategic organizational analytics: hiring health, pipeline
bottlenecks, team analytics, trends, executive KPIs, capacity, forecasts,
benchmarks and optimization opportunities. It provides organizational intelligence
only — **never individual candidate ranking** — marks unavailable metrics honestly
and fabricates no enterprise statistics, trends, KPIs or forecasts.

Importing the package auto-registers the :class:`HiringIntelligenceAgent` with the
AI Platform, the deterministic composer registry and the Multi-Agent Orchestration
registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.hiring_intelligence.agent import (
    HiringIntelligenceAgent,
    HiringIntelligenceInput,
    build_intelligence_evidence,
    hiring_intelligence_agent,
)
from src.ai.agents.hiring_intelligence.analytics_engine import (
    HiringIntelligenceEngine,
    NullWorkforceDataProvider,
    WorkforceDataProvider,
    hiring_intelligence_engine,
)
from src.ai.agents.hiring_intelligence.schemas import (
    HiringIntelligenceReport,
    WorkforceNarrative,
)

__all__ = [
    "HiringIntelligenceAgent",
    "HiringIntelligenceInput",
    "build_intelligence_evidence",
    "hiring_intelligence_agent",
    "HiringIntelligenceEngine",
    "WorkforceDataProvider",
    "NullWorkforceDataProvider",
    "hiring_intelligence_engine",
    "HiringIntelligenceReport",
    "WorkforceNarrative",
]
