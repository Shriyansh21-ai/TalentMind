"""Modules 9 & 10 tests — synchronization framework and enterprise event bus.

Event bus: topic routing, ordering, replay, handler isolation and the
dead-letter queue. Sync: full/incremental/scheduled modes, conflict detection
and resolution, retries, cursor-based recovery and health.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.integrations.events import (
    EnterpriseEventBus,
    EventType,
    topic_matches,
)
from src.platform.integrations.sync import (
    ConflictResolution,
    SyncBatch,
    SyncConflict,
    SyncMode,
    SyncState,
    SynchronizationService,
    detect_conflicts,
    resolve_conflict,
)


# -- event bus --------------------------------------------------------------


def test_topic_matching_rules():
    assert topic_matches("*", "a.b.c")
    assert topic_matches("integration.*", "integration.workday")
    assert not topic_matches("integration.*", "integration.workday.connected")
    assert topic_matches("integration.#", "integration.workday.connected")
    assert topic_matches("a.*.c", "a.b.c")
    assert not topic_matches("a.b", "a.c")


def test_publish_delivers_to_matching_subscribers_only():
    bus = EnterpriseEventBus(clock=FrozenClock())
    seen: list[str] = []
    bus.subscribe("integration.*", lambda e: seen.append(e.topic), subscriber="s1")
    bus.publish("integration.connected", payload={"x": 1})
    bus.publish("sync.completed")
    assert seen == ["integration.connected"]


def test_events_are_ordered_and_replayable():
    bus = EnterpriseEventBus(clock=FrozenClock())
    for i in range(3):
        bus.publish("integration.event", payload={"i": i})
    sequences = [e.sequence for e in bus.history()]
    assert sequences == [1, 2, 3]
    replayed = bus.replay(topic_pattern="integration.*", from_sequence=1)
    assert [e.sequence for e in replayed] == [2, 3]


def test_handler_failure_is_isolated_and_dead_lettered():
    bus = EnterpriseEventBus(clock=FrozenClock())
    ok_calls: list[str] = []

    def boom(_event):
        raise RuntimeError("handler failed")

    bus.subscribe("*", boom, subscriber="bad")
    bus.subscribe("*", lambda e: ok_calls.append(e.topic), subscriber="good")
    bus.publish("integration.connected")
    assert ok_calls == ["integration.connected"]  # good handler still ran
    assert len(bus.dead_letters()) == 1
    assert bus.dead_letters()[0].subscriber == "bad"


def test_event_type_defaults_to_integration():
    bus = EnterpriseEventBus(clock=FrozenClock())
    event = bus.publish("integration.connected")
    assert event.event_type == EventType.INTEGRATION
    assert event.name == "connected"


# -- sync -------------------------------------------------------------------


def test_conflict_detection_and_resolution_helpers():
    conflicts = detect_conflicts(
        "emp_1", {"title": "A", "level": 5}, {"title": "B", "level": 5}
    )
    assert len(conflicts) == 1 and conflicts[0].field == "title"
    resolved = resolve_conflict(conflicts[0], ConflictResolution.SOURCE_WINS)
    assert resolved.resolved and resolved.resolved_value == "A"


def test_scheduled_full_sync_completes_and_resolves_conflicts():
    service = SynchronizationService(clock=FrozenClock())

    def runner(job):
        return SyncBatch(
            records_processed=5,
            conflicts=[
                SyncConflict(entity_id="e1", field="name", source_value="X", target_value="Y")
            ],
            next_cursor="cur-1",
        )

    service._runner = runner
    job = service.schedule("t1", "o1", "intg_1", mode=SyncMode.FULL)
    ran = service.run("t1", job.id)
    assert ran.state == SyncState.COMPLETED
    assert ran.records_processed == 5
    assert ran.cursor == "cur-1"
    assert ran.conflicts[0].resolved  # resolved by default policy


def test_sync_retries_then_fails_then_recovers():
    attempts = {"n": 0}

    def flaky(job):
        attempts["n"] += 1
        if attempts["n"] <= 3:  # fail initial + 2 retries
            return SyncBatch(ok=False, error="transient")
        return SyncBatch(ok=True, records_processed=1, next_cursor="cur-2")

    service = SynchronizationService(runner=flaky, clock=FrozenClock())
    job = service.schedule("t1", "o1", "intg_1", max_retries=2)
    failed = service.run("t1", job.id)
    assert failed.state == SyncState.FAILED
    assert failed.attempts == 3

    recovered = service.recover("t1", job.id)
    assert recovered.state == SyncState.COMPLETED
    assert recovered.cursor == "cur-2"


def test_sync_health_summary():
    service = SynchronizationService(clock=FrozenClock())
    service._runner = lambda job: SyncBatch(records_processed=10)
    job = service.schedule("t1", "o1", "intg_1")
    service.run("t1", job.id)
    health = service.health("t1", "intg_1")
    assert health["total_jobs"] == 1
    assert health["completed"] == 1
    assert health["healthy"] is True
