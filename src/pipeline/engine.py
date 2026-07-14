"""Hiring Pipeline Engine — validated recruiter-workflow mutations.

This is the behavioural core of Module 1. Every function operates on a
:class:`PipelineStore` (injectable for testing and isolation), reads the current
:class:`CandidatePipelineStatus`, applies a single validated mutation, stamps the
audit trail, and persists the result.

Stage transitions are validated against the declarative rules in
``src/pipeline/models.py`` — an illegal move raises :class:`InvalidTransition`
rather than silently corrupting the funnel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union

from src.pipeline.models import (
    CandidatePipelineStatus,
    PipelineStage,
    Priority,
    StageEvent,
    can_transition,
    next_stage,
)
from src.pipeline.store import PipelineStore

StageLike = Union[PipelineStage, str]
PriorityLike = Union[Priority, str]


class InvalidTransition(ValueError):
    """Raised when a requested stage transition violates the funnel rules."""


class PipelineError(RuntimeError):
    """Raised for non-transition pipeline errors (e.g. unknown candidate)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _coerce_stage(stage: StageLike) -> PipelineStage:
    """Coerce a stage-or-string into a :class:`PipelineStage`."""
    if isinstance(stage, PipelineStage):
        return stage
    return PipelineStage.from_value(stage)


def _coerce_priority(priority: PriorityLike) -> Priority:
    """Coerce a priority-or-string into a :class:`Priority`."""
    if isinstance(priority, Priority):
        return priority
    return Priority(priority)


def get_or_create(
    candidate_id: str,
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Return the candidate's pipeline status, creating it at ``APPLIED`` if new.

    Args:
        candidate_id: The candidate to look up.
        store: Persistence backend (a default :class:`PipelineStore` is used when
            omitted — the dependency-injection seam used by tests).
        timestamp: Injected ISO timestamp for the initial event (defaults to now).

    Returns:
        The existing or newly-created :class:`CandidatePipelineStatus`.
    """
    store = store or PipelineStore()
    existing = store.get(candidate_id)
    if existing is not None:
        return existing

    stamp = timestamp or _now_iso()
    status = CandidatePipelineStatus(
        candidate_id=candidate_id,
        current_stage=PipelineStage.APPLIED,
        last_updated=stamp,
        stage_history=[
            StageEvent(
                to_stage=PipelineStage.APPLIED.value,
                from_stage=None,
                timestamp=stamp,
                actor=None,
                note="Entered pipeline",
            )
        ],
    )
    status.status = status.derive_status()
    store.put(status)
    return status


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def update_stage(
    candidate_id: str,
    target_stage: StageLike,
    actor: Optional[str] = None,
    note: Optional[str] = None,
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Move a candidate to an explicit ``target_stage`` after validating the move.

    Args:
        candidate_id: The candidate to transition.
        target_stage: Destination :class:`PipelineStage` (or its display string).
        actor: Recruiter performing the transition (recorded in the audit trail).
        note: Optional note attached to the transition.
        store: Persistence backend (injectable; defaults to :class:`PipelineStore`).
        timestamp: Injected ISO timestamp (defaults to now) — kept explicit so the
            transition logic is deterministic under test.

    Returns:
        The updated :class:`CandidatePipelineStatus`.

    Raises:
        InvalidTransition: If moving from the current stage to ``target_stage`` is
            not permitted by the funnel rules.
    """
    store = store or PipelineStore()
    status = get_or_create(candidate_id, store=store, timestamp=timestamp)

    target = _coerce_stage(target_stage)
    source = status.current_stage

    if not can_transition(source, target):
        raise InvalidTransition(
            f"Illegal transition for {candidate_id}: "
            f"{source.value} -> {target.value}"
        )

    stamp = timestamp or _now_iso()

    # A same-stage move is a valid no-op; still record it for a complete trail.
    status.stage_history.append(
        StageEvent(
            to_stage=target.value,
            from_stage=source.value,
            timestamp=stamp,
            actor=actor,
            note=note,
        )
    )
    status.current_stage = target
    status.status = status.derive_status()
    status.last_updated = stamp

    store.put(status)
    return status


def move_candidate(
    candidate_id: str,
    target_stage: Optional[StageLike] = None,
    actor: Optional[str] = None,
    note: Optional[str] = None,
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Advance a candidate to ``target_stage``, or one step forward if omitted.

    This is the recruiter-facing convenience entry point. When ``target_stage`` is
    ``None`` the candidate is advanced to the next forward funnel stage; if they
    are already at a terminal stage a :class:`PipelineError` is raised. All
    validation is delegated to :func:`update_stage`.

    Args:
        candidate_id: The candidate to move.
        target_stage: Explicit destination, or ``None`` to auto-advance.
        actor: Recruiter performing the move.
        note: Optional transition note.
        store: Persistence backend (injectable).
        timestamp: Injected ISO timestamp (defaults to now).

    Returns:
        The updated :class:`CandidatePipelineStatus`.

    Raises:
        PipelineError: If auto-advancing from a terminal stage.
        InvalidTransition: If the resolved transition is illegal.
    """
    store = store or PipelineStore()

    if target_stage is None:
        status = get_or_create(candidate_id, store=store, timestamp=timestamp)
        following = next_stage(status.current_stage)
        if following is None:
            raise PipelineError(
                f"{candidate_id} is at terminal stage "
                f"{status.current_stage.value}; specify an explicit target."
            )
        target_stage = following

    return update_stage(
        candidate_id,
        target_stage,
        actor=actor,
        note=note,
        store=store,
        timestamp=timestamp,
    )


def add_note(
    candidate_id: str,
    note: str,
    actor: Optional[str] = None,
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Append a free-text recruiter note without changing the candidate's stage.

    Args:
        candidate_id: The candidate to annotate.
        note: Note text (blank / whitespace-only notes are ignored).
        actor: Recruiter authoring the note (prefixed to the stored line).
        store: Persistence backend (injectable).
        timestamp: Injected ISO timestamp (defaults to now).

    Returns:
        The updated :class:`CandidatePipelineStatus`.
    """
    store = store or PipelineStore()
    status = get_or_create(candidate_id, store=store, timestamp=timestamp)

    text = (note or "").strip()
    if text:
        stamp = timestamp or _now_iso()
        prefix = f"[{stamp}]"
        if actor:
            prefix += f" {actor}:"
        status.notes.append(f"{prefix} {text}")
        status.last_updated = stamp
        store.put(status)

    return status


def assign_recruiter(
    candidate_id: str,
    recruiter: Optional[str],
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Set (or clear, with ``None``) the owning recruiter for a candidate.

    Args:
        candidate_id: The candidate to (re)assign.
        recruiter: Recruiter id / name, or ``None`` to unassign.
        store: Persistence backend (injectable).
        timestamp: Injected ISO timestamp (defaults to now).

    Returns:
        The updated :class:`CandidatePipelineStatus`.
    """
    store = store or PipelineStore()
    status = get_or_create(candidate_id, store=store, timestamp=timestamp)

    status.assigned_recruiter = recruiter
    status.last_updated = timestamp or _now_iso()
    store.put(status)
    return status


def change_priority(
    candidate_id: str,
    priority: PriorityLike,
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Update a candidate's recruiter-assigned priority.

    Args:
        candidate_id: The candidate to reprioritize.
        priority: New :class:`Priority` (or its display string).
        store: Persistence backend (injectable).
        timestamp: Injected ISO timestamp (defaults to now).

    Returns:
        The updated :class:`CandidatePipelineStatus`.
    """
    store = store or PipelineStore()
    status = get_or_create(candidate_id, store=store, timestamp=timestamp)

    status.priority = _coerce_priority(priority)
    status.last_updated = timestamp or _now_iso()
    store.put(status)
    return status


def add_tag(
    candidate_id: str,
    tag: str,
    store: Optional[PipelineStore] = None,
    timestamp: Optional[str] = None,
) -> CandidatePipelineStatus:
    """Attach a de-duplicated recruiter tag to a candidate.

    Args:
        candidate_id: The candidate to tag.
        tag: Tag label (blank tags and duplicates are ignored).
        store: Persistence backend (injectable).
        timestamp: Injected ISO timestamp (defaults to now).

    Returns:
        The updated :class:`CandidatePipelineStatus`.
    """
    store = store or PipelineStore()
    status = get_or_create(candidate_id, store=store, timestamp=timestamp)

    label = (tag or "").strip()
    if label and label not in status.tags:
        status.tags.append(label)
        status.last_updated = timestamp or _now_iso()
        store.put(status)

    return status
