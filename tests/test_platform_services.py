"""Tests for Modules 5-7 — Workspaces, Configuration, Subscriptions."""

from __future__ import annotations

from datetime import UTC

import faiss  # noqa: F401
import pytest

from src.platform.common import (
    FrozenClock,
    QuotaExceededError,
    TenantIsolationError,
)
from src.platform.config import ConfigurationService, License, LocalizationSettings
from src.platform.subscription import Meter, PlanTier, SubscriptionService
from src.platform.workspaces import WorkspaceKind, WorkspaceService

T = O = "org_1"


# -- workspaces (Module 5) --------------------------------------------------


def test_workspace_owns_resources():
    ws = WorkspaceService(clock=FrozenClock())
    w = ws.create_workspace(T, O, "Hiring", kind=WorkspaceKind.HIRING)
    ws.add_project(T, w.id, "Backend Req")
    ws.add_pipeline(T, w.id, "Standard")
    ws.add_member(T, w.id, "u1", role="recruiter")
    ws.add_team(T, w.id, "Panel")
    ws.bind_agent(T, w.id, "hiring_analyst")
    ws.add_knowledge_base(T, w.id, "Playbook")
    ws.add_report(T, w.id, "Weekly")
    ws.add_dashboard(T, w.id, "Funnel")
    assert len(ws.projects(T, w.id)) == 1
    assert len(ws.pipelines(T, w.id)) == 1
    assert len(ws.members(T, w.id)) == 1
    assert ws.agent_bindings(T, w.id)[0].agent_key == "hiring_analyst"


def test_workspace_child_creation_is_tenant_isolated():
    ws = WorkspaceService(clock=FrozenClock())
    w = ws.create_workspace(T, O, "Hiring")
    with pytest.raises(TenantIsolationError):
        ws.add_project("org_2", w.id, "x")  # foreign tenant, same workspace id


def test_workspace_quota_enforced():
    ws = WorkspaceService(clock=FrozenClock())
    ws.create_workspace(T, O, "A", max_workspaces=1)
    with pytest.raises(QuotaExceededError):
        ws.create_workspace(T, O, "B", max_workspaces=1)


# -- configuration (Module 6) ----------------------------------------------


def test_feature_flags_and_cache():
    cfg = ConfigurationService(clock=FrozenClock())
    cfg.ensure(T, O)
    cfg.set_feature(T, "beta", True)
    assert cfg.is_feature_enabled(T, "beta")
    assert not cfg.is_feature_enabled(T, "missing")
    # cache is populated after a read
    assert cfg.cache.get(T, "configuration") is not None


def test_require_feature_raises_when_disabled():
    from src.platform.common.errors import FeatureDisabledError

    cfg = ConfigurationService(clock=FrozenClock())
    cfg.ensure(T, O)
    with pytest.raises(FeatureDisabledError):
        cfg.require_feature(T, "beta")


def test_licensing_entitlements():
    from datetime import datetime

    cfg = ConfigurationService(clock=FrozenClock())
    cfg.ensure(T, O)
    cfg.set_license(
        T,
        License(
            plan="business",
            entitlements=["audit_export"],
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
        ),
    )
    assert cfg.is_licensed_for(T, "audit_export")
    assert not cfg.is_licensed_for(T, "sso")


def test_localization_update_persists():
    cfg = ConfigurationService(clock=FrozenClock())
    cfg.ensure(T, O)
    cfg.update(T, localization=LocalizationSettings(language="fr", locale="fr-FR"))
    assert cfg.get(T).localization.language == "fr"


# -- subscription (Module 7) ------------------------------------------------


def test_subscribe_seeds_meters_from_plan():
    sub = SubscriptionService(clock=FrozenClock())
    sub.subscribe(T, O, PlanTier.PROFESSIONAL)
    assert sub.remaining(T, Meter.SEATS) == 10
    assert sub.remaining(T, Meter.AI_CREDITS) == 25_000


def test_usage_quota_enforced():
    sub = SubscriptionService(clock=FrozenClock())
    sub.subscribe(T, O, PlanTier.FREE)
    sub.record_usage(T, Meter.AI_CREDITS, 1_000)
    with pytest.raises(QuotaExceededError):
        sub.record_usage(T, Meter.AI_CREDITS, 1)


def test_seat_allocate_and_release():
    sub = SubscriptionService(clock=FrozenClock())
    sub.subscribe(T, O, PlanTier.PROFESSIONAL)
    sub.allocate_seat(T)
    assert sub.remaining(T, Meter.SEATS) == 9
    sub.release_seat(T)
    assert sub.remaining(T, Meter.SEATS) == 10


def test_change_plan_to_enterprise_unlimited():
    sub = SubscriptionService(clock=FrozenClock())
    sub.subscribe(T, O, PlanTier.FREE)
    sub.record_usage(T, Meter.AI_CREDITS, 500)
    sub.change_plan(T, PlanTier.ENTERPRISE)
    assert sub.remaining(T, Meter.AI_CREDITS) is None  # unlimited
    assert sub.require(T).meter(Meter.AI_CREDITS).used == 500  # usage preserved


def test_duplicate_subscription_rejected():
    from src.platform.common.errors import ConflictError

    sub = SubscriptionService(clock=FrozenClock())
    sub.subscribe(T, O, PlanTier.FREE)
    with pytest.raises(ConflictError):
        sub.subscribe(T, O, PlanTier.FREE)


def test_billing_hook_fires():
    from src.platform.subscription.models import Subscription

    events: list[str] = []

    class RecordingHook:
        def on_subscription_created(self, s: Subscription) -> None:
            events.append("created")

        def on_plan_changed(self, s: Subscription, previous) -> None:
            events.append("changed")

        def on_usage_recorded(self, s, meter, amount) -> None:
            events.append("usage")

    sub = SubscriptionService(billing_hook=RecordingHook(), clock=FrozenClock())
    sub.subscribe(T, O, PlanTier.FREE)
    sub.record_usage(T, Meter.AI_CREDITS, 10)
    sub.change_plan(T, PlanTier.BUSINESS)
    assert events == ["created", "usage", "changed"]
