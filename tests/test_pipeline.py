"""Tests for the Hiring Pipeline Engine (Module 1)."""

from __future__ import annotations

import pytest

from src.pipeline.engine import (
    InvalidTransition,
    PipelineError,
    add_note,
    add_tag,
    assign_recruiter,
    change_priority,
    get_or_create,
    move_candidate,
    update_stage,
)
from src.pipeline.models import PipelineStage, Priority, can_transition, next_stage
from src.pipeline.store import PipelineStore

STAMP = "2026-07-14T00:00:00+00:00"


@pytest.fixture
def store(tmp_path):
    """A PipelineStore backed by an isolated temp file (DI seam)."""
    return PipelineStore(path=str(tmp_path / "pipeline_state.json"))


def test_new_candidate_starts_applied(store):
    status = get_or_create("C1", store=store, timestamp=STAMP)
    assert status.current_stage == PipelineStage.APPLIED
    assert status.status == "Active"
    assert len(status.stage_history) == 1
    assert status.priority == Priority.MEDIUM


def test_valid_forward_transition(store):
    update_stage("C1", PipelineStage.SHORTLISTED, store=store, timestamp=STAMP)
    status = store.get("C1")
    assert status.current_stage == PipelineStage.SHORTLISTED
    assert status.stage_history[-1].from_stage == "Applied"
    assert status.stage_history[-1].to_stage == "Shortlisted"


def test_invalid_transition_raises(store):
    # Applied -> Offer is a multi-step forward jump and is not allowed.
    with pytest.raises(InvalidTransition):
        update_stage("C1", PipelineStage.OFFER, store=store, timestamp=STAMP)


def test_reject_allowed_from_any_stage(store):
    update_stage("C1", PipelineStage.REJECTED, store=store, timestamp=STAMP)
    status = store.get("C1")
    assert status.current_stage == PipelineStage.REJECTED
    assert status.status == "Rejected"


def test_move_candidate_auto_advances(store):
    get_or_create("C1", store=store, timestamp=STAMP)
    move_candidate("C1", store=store, timestamp=STAMP)  # -> Shortlisted
    move_candidate("C1", store=store, timestamp=STAMP)  # -> Recruiter Review
    assert store.get("C1").current_stage == PipelineStage.RECRUITER_REVIEW


def test_move_candidate_terminal_raises(store):
    update_stage("C1", PipelineStage.REJECTED, store=store, timestamp=STAMP)
    with pytest.raises(PipelineError):
        move_candidate("C1", store=store, timestamp=STAMP)


def test_full_happy_path_to_hired(store):
    path = [
        PipelineStage.SHORTLISTED,
        PipelineStage.RECRUITER_REVIEW,
        PipelineStage.TECHNICAL_INTERVIEW,
        PipelineStage.HIRING_MANAGER,
        PipelineStage.HR_INTERVIEW,
        PipelineStage.OFFER,
        PipelineStage.OFFER_ACCEPTED,
    ]
    for stage in path:
        update_stage("C1", stage, store=store, timestamp=STAMP)
    status = store.get("C1")
    assert status.current_stage == PipelineStage.OFFER_ACCEPTED
    assert status.status == "Hired"


def test_add_note_and_recruiter_and_priority(store):
    add_note("C1", "Great portfolio", actor="alice", store=store, timestamp=STAMP)
    assign_recruiter("C1", "alice", store=store, timestamp=STAMP)
    change_priority("C1", Priority.HIGH, store=store, timestamp=STAMP)
    add_tag("C1", "referral", store=store, timestamp=STAMP)
    add_tag("C1", "referral", store=store, timestamp=STAMP)  # dedup

    status = store.get("C1")
    assert any("Great portfolio" in n for n in status.notes)
    assert status.assigned_recruiter == "alice"
    assert status.priority == Priority.HIGH
    assert status.tags == ["referral"]


def test_blank_note_ignored(store):
    add_note("C1", "   ", store=store, timestamp=STAMP)
    assert store.get("C1").notes == []


def test_persistence_round_trip(store):
    change_priority("C1", "Urgent", store=store, timestamp=STAMP)
    update_stage("C1", PipelineStage.SHORTLISTED, store=store, timestamp=STAMP)

    reloaded = PipelineStore(path=store.path)
    status = reloaded.get("C1")
    assert status.priority == Priority.URGENT
    assert status.current_stage == PipelineStage.SHORTLISTED


def test_transition_helpers():
    assert can_transition(PipelineStage.APPLIED, PipelineStage.SHORTLISTED)
    assert not can_transition(PipelineStage.APPLIED, PipelineStage.OFFER)
    assert can_transition(PipelineStage.APPLIED, PipelineStage.APPLIED)  # no-op
    assert next_stage(PipelineStage.APPLIED) == PipelineStage.SHORTLISTED
    assert next_stage(PipelineStage.OFFER_ACCEPTED) is None


def test_stage_from_value_tolerant():
    assert PipelineStage.from_value("Technical Interview") == PipelineStage.TECHNICAL_INTERVIEW
    assert PipelineStage.from_value("TECHNICAL_INTERVIEW") == PipelineStage.TECHNICAL_INTERVIEW
    with pytest.raises(ValueError):
        PipelineStage.from_value("Nonsense")
