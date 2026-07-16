"""Module 7 — Subscription Architecture.

Five plan tiers (Free → Custom) with seats, AI credits, storage and API-limit
meters, quota-enforced usage recording, plan changes, and a future billing hook
seam. No payment integration — the platform emits billing events, it does not
charge.
"""

from __future__ import annotations

from src.platform.subscription.models import (
    BillingHook,
    Meter,
    NullBillingHook,
    Subscription,
    SubscriptionStatus,
    UsageState,
)
from src.platform.subscription.plans import (
    PLAN_CATALOG,
    PlanDefinition,
    PlanTier,
    plan_for,
)
from src.platform.subscription.service import SubscriptionService

__all__ = [
    "PlanTier",
    "PlanDefinition",
    "PLAN_CATALOG",
    "plan_for",
    "Subscription",
    "SubscriptionStatus",
    "Meter",
    "UsageState",
    "BillingHook",
    "NullBillingHook",
    "SubscriptionService",
]
