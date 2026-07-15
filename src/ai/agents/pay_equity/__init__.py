"""Enterprise Internal Pay Equity & Fairness Intelligence System (Phase 5 / M2).

The Pay Equity Guardian answers whether an offer is internally fair, whether it
creates salary compression or promotion inequity, whether it aligns with company
pay philosophy and whether executives should review it. It is **not** a bias
detector and **not** a legal decision engine — it consumes existing intelligence
(reusing the Compensation Governance Agent) plus optional injected HRIS data, and
surfaces governance risks and human-review needs only. It fabricates no payroll,
never accuses discrimination and never concludes a legal violation.

Importing the package auto-registers the :class:`PayEquityGuardianAgent` with the
AI Platform, the deterministic composer registry and the Multi-Agent Orchestration
registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.pay_equity.agent import (
    PayEquityGuardianAgent,
    PayEquityInput,
    build_pay_equity_evidence,
    pay_equity_agent,
)
from src.ai.agents.pay_equity.equity_engine import (
    NullPayEquityDataProvider,
    PayEquityDataProvider,
    PayEquityGuardianEngine,
    pay_equity_guardian_engine,
)
from src.ai.agents.pay_equity.schemas import (
    PayEquityNarrative,
    PayEquityReport,
)

__all__ = [
    "PayEquityGuardianAgent",
    "PayEquityInput",
    "build_pay_equity_evidence",
    "pay_equity_agent",
    "PayEquityGuardianEngine",
    "PayEquityDataProvider",
    "NullPayEquityDataProvider",
    "pay_equity_guardian_engine",
    "PayEquityNarrative",
    "PayEquityReport",
]
