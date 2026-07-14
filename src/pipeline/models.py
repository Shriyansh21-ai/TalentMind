"""Domain models for the Hiring Pipeline Engine.

Defines the recruiter workflow as an explicit state machine: the ordered set of
:class:`PipelineStage` states, a candidate :class:`Priority`, and the
:class:`CandidatePipelineStatus` record that tracks a single candidate's journey
through the funnel (current stage, full audit trail, ownership, notes, tags).

This module is pure data + a declarative transition map. All mutation happens in
``src/pipeline/engine.py``; all persistence happens in ``src/pipeline/store.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class PipelineStage(str, Enum):
    """Ordered stages of the enterprise hiring funnel.

    Inherits from ``str`` so values serialize directly to JSON and compare
    cleanly against stored strings. The declaration order defines the canonical
    "forward" progression of the funnel; ``REJECTED`` and ``HOLD`` are terminal /
    parking states reachable from any active stage.
    """

    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    RECRUITER_REVIEW = "Recruiter Review"
    TECHNICAL_INTERVIEW = "Technical Interview"
    HIRING_MANAGER = "Hiring Manager"
    HR_INTERVIEW = "HR Interview"
    OFFER = "Offer"
    OFFER_ACCEPTED = "Offer Accepted"
    REJECTED = "Rejected"
    HOLD = "Hold"

    @classmethod
    def from_value(cls, value: str) -> "PipelineStage":
        """Resolve a stage from its display value, tolerant of raw enum names.

        Args:
            value: A stage display string (``"Technical Interview"``) or enum
                name (``"TECHNICAL_INTERVIEW"``).

        Returns:
            The matching :class:`PipelineStage`.

        Raises:
            ValueError: If ``value`` matches no known stage.
        """
        for stage in cls:
            if value == stage.value or value == stage.name:
                return stage
        raise ValueError(f"Unknown pipeline stage: {value!r}")


class Priority(str, Enum):
    """Recruiter-assigned candidate priority."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


# ---------------------------------------------------------------------------
# Transition rules
# ---------------------------------------------------------------------------

# Stages a candidate can always be moved to from any active stage. Rejecting or
# parking a candidate is a valid action at every point in the funnel.
_ALWAYS_ALLOWED: Set[PipelineStage] = {PipelineStage.REJECTED, PipelineStage.HOLD}

# Forward funnel order used to derive the default "advance to next stage" target
# and to validate one-step-forward / any-step-back transitions.
_FUNNEL_ORDER: List[PipelineStage] = [
    PipelineStage.APPLIED,
    PipelineStage.SHORTLISTED,
    PipelineStage.RECRUITER_REVIEW,
    PipelineStage.TECHNICAL_INTERVIEW,
    PipelineStage.HIRING_MANAGER,
    PipelineStage.HR_INTERVIEW,
    PipelineStage.OFFER,
    PipelineStage.OFFER_ACCEPTED,
]

# Explicit allowed-transition map. Each active stage may advance one step, move
# to any always-allowed state, and (except from APPLIED) step back to earlier
# active stages. Terminal states can be re-opened to HOLD or moved back into the
# active funnel, which mirrors how real ATS tools let recruiters "reconsider".
_ALLOWED_TRANSITIONS: Dict[PipelineStage, Set[PipelineStage]] = {}


def _build_transition_map() -> None:
    """Populate ``_ALLOWED_TRANSITIONS`` from the funnel order + parking rules."""
    for position, stage in enumerate(_FUNNEL_ORDER):
        allowed: Set[PipelineStage] = set(_ALWAYS_ALLOWED)

        # Advance exactly one step forward.
        if position + 1 < len(_FUNNEL_ORDER):
            allowed.add(_FUNNEL_ORDER[position + 1])

        # Step back to any earlier active stage (recruiters revisit candidates).
        allowed.update(_FUNNEL_ORDER[:position])

        _ALLOWED_TRANSITIONS[stage] = allowed

    # OFFER_ACCEPTED is a success terminal — only parking to HOLD is meaningful.
    _ALLOWED_TRANSITIONS[PipelineStage.OFFER_ACCEPTED] = {PipelineStage.HOLD}

    # Parking / rejection states can be re-activated back into the funnel.
    reactivation = set(_FUNNEL_ORDER) | {PipelineStage.HOLD, PipelineStage.REJECTED}
    _ALLOWED_TRANSITIONS[PipelineStage.HOLD] = reactivation - {PipelineStage.HOLD}
    _ALLOWED_TRANSITIONS[PipelineStage.REJECTED] = {
        PipelineStage.SHORTLISTED,
        PipelineStage.RECRUITER_REVIEW,
        PipelineStage.HOLD,
    }


_build_transition_map()


def allowed_transitions(stage: PipelineStage) -> Set[PipelineStage]:
    """Return the set of stages reachable in one move from ``stage``."""
    return set(_ALLOWED_TRANSITIONS.get(stage, set()))


def can_transition(source: PipelineStage, target: PipelineStage) -> bool:
    """Return ``True`` iff moving from ``source`` to ``target`` is permitted.

    Moving to the same stage is always treated as a valid no-op transition.
    """
    if source == target:
        return True
    return target in allowed_transitions(source)


def next_stage(stage: PipelineStage) -> Optional[PipelineStage]:
    """Return the default forward stage after ``stage``, or ``None`` if terminal."""
    if stage in _FUNNEL_ORDER:
        position = _FUNNEL_ORDER.index(stage)
        if position + 1 < len(_FUNNEL_ORDER):
            return _FUNNEL_ORDER[position + 1]
    return None


@dataclass
class StageEvent:
    """A single, immutable entry in a candidate's stage-transition audit trail.

    Attributes:
        from_stage: Stage the candidate moved out of (``None`` for the first entry).
        to_stage: Stage the candidate moved into.
        timestamp: ISO-8601 timestamp of the transition (injected by the caller
            so the pipeline core stays deterministic and testable).
        actor: Who performed the transition (recruiter id / name).
        note: Optional free-text note attached to the transition.
    """

    to_stage: str
    timestamp: str
    from_stage: Optional[str] = None
    actor: Optional[str] = None
    note: Optional[str] = None


@dataclass
class CandidatePipelineStatus:
    """Full pipeline state for one candidate.

    Attributes:
        candidate_id: Stable candidate identifier.
        current_stage: The candidate's current :class:`PipelineStage`.
        stage_history: Ordered audit trail of every transition.
        status: Coarse lifecycle label (``Active`` / ``Rejected`` / ``Hired`` /
            ``On Hold``) derived from ``current_stage``.
        assigned_recruiter: Owning recruiter (``None`` if unassigned).
        priority: Recruiter-assigned :class:`Priority`.
        last_updated: ISO-8601 timestamp of the most recent mutation.
        notes: Chronological free-text recruiter notes.
        tags: Arbitrary recruiter labels for filtering / segmentation.
    """

    candidate_id: str
    current_stage: PipelineStage = PipelineStage.APPLIED
    stage_history: List[StageEvent] = field(default_factory=list)
    status: str = "Active"
    assigned_recruiter: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    last_updated: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def derive_status(self) -> str:
        """Return the coarse lifecycle label implied by the current stage."""
        if self.current_stage == PipelineStage.REJECTED:
            return "Rejected"
        if self.current_stage == PipelineStage.OFFER_ACCEPTED:
            return "Hired"
        if self.current_stage == PipelineStage.HOLD:
            return "On Hold"
        return "Active"
