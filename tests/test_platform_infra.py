"""Tests for Modules 8-12 — Notifications, Audit, API, Storage, Developer."""

from __future__ import annotations

from datetime import timedelta

import faiss  # noqa: F401
import pytest

from src.platform.api import (
    FilterSpec,
    Operator,
    PageRequest,
    SortSpec,
    TokenBucketRateLimiter,
    apply_filters,
    apply_sorts,
    build_openapi,
    cursor_paginate,
    negotiate,
    paginate,
    to_response,
)
from src.platform.audit import AuditCategory, InMemoryAuditSink, PlatformAuditService
from src.platform.common import FrozenClock
from src.platform.common.errors import NotFoundError
from src.platform.developer import (
    Event,
    EventBus,
    ExtensionRegistry,
    HookRegistry,
    PluginManifest,
)
from src.platform.notifications import (
    Channel,
    DeliveryStatus,
    InMemoryChannel,
    NotificationService,
)
from src.platform.storage import InMemoryVectorStore, StorageClass, StorageService

T = O = "org_1"


# -- notifications (Module 8) ----------------------------------------------


def test_template_render_and_delivery():
    ns = NotificationService(clock=FrozenClock())
    channel = InMemoryChannel(Channel.EMAIL)
    ns.register_channel(channel)
    ns.register_template(
        T,
        O,
        "welcome",
        channel=Channel.EMAIL,
        subject_template="Hi {name}",
        body_template="Welcome, {name}!",
    )
    n = ns.send(T, O, "u1", template_key="welcome", context={"name": "Jane"})
    assert n.status == DeliveryStatus.SENT
    assert channel.outbox[0].subject == "Hi Jane"


def test_preference_suppresses_channel():
    ns = NotificationService(clock=FrozenClock())
    ns.set_preference(T, O, "u2", {"sms": False})
    n = ns.send(T, O, "u2", channel=Channel.SMS, subject="x")
    assert n.status == DeliveryStatus.SUPPRESSED


def test_scheduled_notification_flushes_when_due():
    clock = FrozenClock()
    ns = NotificationService(clock=clock)
    ns.send(
        T,
        O,
        "u1",
        channel=Channel.IN_APP,
        subject="later",
        scheduled_for=clock.now() + timedelta(hours=2),
    )
    assert ns.flush_due(T) == 0  # not yet due
    clock.advance(days=1)
    assert ns.flush_due(T) == 1


# -- audit (Module 9) -------------------------------------------------------


def test_audit_chain_and_tamper_detection():
    au = PlatformAuditService(clock=FrozenClock())
    sink = InMemoryAuditSink()
    au.add_sink(sink)
    au.record(T, O, AuditCategory.AUTHENTICATION, "login", actor_id="u1")
    au.record(T, O, AuditCategory.PERMISSION, "grant", actor_id="admin")
    assert au.verify_chain(T)
    assert len(sink.events) == 2
    au.repo.list(tenant_id=T)[0].action = "TAMPERED"
    assert not au.verify_chain(T)


def test_audit_query_and_isolation():
    au = PlatformAuditService(clock=FrozenClock())
    au.record(T, O, AuditCategory.SETTINGS, "update")
    au.record("org_2", "org_2", AuditCategory.SETTINGS, "update")
    assert len(au.query(T)) == 1
    assert len(au.query(T, category=AuditCategory.AUTHENTICATION)) == 0


# -- api (Module 10) --------------------------------------------------------


def test_offset_pagination():
    page = paginate(list(range(1, 101)), PageRequest(page=2, size=10))
    assert page.items[0] == 11
    assert page.total_pages == 10
    assert page.has_next


def test_cursor_pagination_walks_forward():
    items = list(range(1, 101))
    first = cursor_paginate(items, size=10)
    second = cursor_paginate(items, cursor=first.next_cursor, size=10)
    assert first.items[0] == 1 and second.items[0] == 11
    assert first.has_more


def test_filtering_and_sorting():
    class Row:
        def __init__(self, a, b):
            self.a, self.b = a, b

    rows = [Row(1, "x"), Row(3, "y"), Row(2, "z")]
    assert [r.a for r in apply_sorts(rows, [SortSpec(field="a")])] == [1, 2, 3]
    assert [r.a for r in apply_sorts(rows, [SortSpec(field="a", descending=True)])] == [3, 2, 1]
    filtered = apply_filters(rows, [FilterSpec(field="a", op=Operator.GTE, value=2)])
    assert len(filtered) == 2


def test_version_negotiation_and_error_mapping():
    assert negotiate("v9").value == "v1"
    assert negotiate("v1").value == "v1"
    resp = to_response(NotFoundError("gone"))
    assert resp.success is False and resp.error.code == "not_found"
    assert build_openapi()["openapi"] == "3.1.0"


def test_rate_limiter_token_bucket():
    limiter = TokenBucketRateLimiter(2, clock=FrozenClock())
    assert limiter.check("t").allowed
    assert limiter.check("t").allowed
    assert not limiter.check("t").allowed  # bucket drained


# -- storage (Module 11) ----------------------------------------------------


def test_storage_put_get_and_usage():
    ss = StorageService(clock=FrozenClock())
    obj = ss.put(T, O, "resume.pdf", b"hello", storage_class=StorageClass.DOCUMENT)
    assert ss.get(T, "resume.pdf", storage_class=StorageClass.DOCUMENT) == b"hello"
    assert ss.usage_bytes(T) == 5
    assert obj.cdn_url


def test_storage_missing_raises():
    ss = StorageService(clock=FrozenClock())
    with pytest.raises(NotFoundError):
        ss.get(T, "nope")


def test_vector_store_is_tenant_isolated():
    vs = InMemoryVectorStore()
    vs.upsert(T, "c1", [1.0, 0.0], {})
    vs.upsert(T, "c2", [0.0, 1.0], {})
    vs.upsert("org_2", "c3", [1.0, 0.0], {})
    top = vs.query(T, [1.0, 0.1], top_k=5)
    ids = [i for i, _ in top]
    assert ids[0] == "c1" and "c3" not in ids  # no cross-tenant vectors


# -- developer platform (Module 12) ----------------------------------------


def test_event_bus_isolates_handler_errors():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("x", lambda e: seen.append("a"))
    bus.subscribe("x", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
    bus.subscribe("x", lambda e: seen.append("c"))
    results = bus.publish(Event(name="x"))
    assert seen == ["a", "c"]  # one failing handler didn't stop the others
    assert [r.ok for r in results] == [True, False, True]


def test_hooks_apply_in_priority_order():
    hooks = HookRegistry()
    hooks.add("score", lambda v, **c: v + 1, priority=20)
    hooks.add("score", lambda v, **c: v * 2, priority=10)
    assert hooks.apply_filters("score", 5) == 11  # (5*2)+1


def test_plugin_lifecycle():
    reg = ExtensionRegistry()

    class DemoPlugin:
        manifest = PluginManifest(id="p1", name="Demo")

        def __init__(self):
            self.active = False

        def activate(self, sdk):
            self.active = True
            sdk.log("activated")

        def deactivate(self):
            self.active = False

    plugin = DemoPlugin()
    reg.register(plugin)
    reg.enable("p1")
    assert plugin.active
    reg.disable("p1")
    assert not plugin.active
    assert reg.list()[0].manifest.id == "p1"
