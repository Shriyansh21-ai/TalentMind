"""Domain models for Talent Pool Segmentation (Module 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TalentPool(str, Enum):
    """Recruiter-facing talent segments.

    Pools span three orthogonal axes so a candidate can belong to several at once:

    * **Readiness** — Immediate Hire, High Potential, Future Pipeline,
      Needs Upskilling.
    * **Shape** — Leadership Talent, Specialist, Generalist, Senior Engineering.
    * **Domain** — ML Specialists, Frontend, Backend, Cloud, Data.
    """

    # Readiness
    IMMEDIATE_HIRE = "Immediate Hire"
    HIGH_POTENTIAL = "High Potential"
    FUTURE_PIPELINE = "Future Pipeline"
    NEEDS_UPSKILLING = "Needs Upskilling"

    # Shape
    LEADERSHIP_TALENT = "Leadership Talent"
    SENIOR_ENGINEERING = "Senior Engineering"
    SPECIALIST = "Specialist"
    GENERALIST = "Generalist"

    # Domain
    ML_SPECIALISTS = "ML Specialists"
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    CLOUD = "Cloud"
    DATA = "Data"


@dataclass
class PoolAssignment:
    """The set of pools a single candidate has been segmented into.

    Attributes:
        candidate_id: Stable candidate identifier.
        pools: All pools the candidate qualifies for (may be empty).
        rationale: Human-readable reason strings, keyed for the UI, explaining
            why each pool was assigned (kept for explainability / auditing).
    """

    candidate_id: str
    pools: List[TalentPool] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)

    def in_pool(self, pool: TalentPool) -> bool:
        """Return ``True`` iff the candidate belongs to ``pool``."""
        return pool in self.pools
