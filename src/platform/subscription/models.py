"""Subscription domain models (Module 7).

A tenant holds one :class:`Subscription`; usage across metered dimensions
(seats, AI credits, storage, API requests) is tracked on it. The
:class:`BillingHook` protocol is the seam a future billing/payment provider
implements — the platform emits events, it does not charge anyone.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity
from src.platform.subscription.plans import PlanTier


class SubscriptionStatus(str, Enum):
    """State of a subscription."""

    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class Meter(str, Enum):
    """The metered usage dimensions."""

    SEATS = "seats"
    AI_CREDITS = "ai_credits"
    STORAGE_GB = "storage_gb"
    API_REQUESTS = "api_requests"


class UsageState(PlatformModel):
    """Current usage vs. limit for one metered dimension."""

    meter: Meter
    used: int = 0
    limit: int | None = None  # None => unlimited

    def remaining(self) -> int | None:
        """Return remaining allowance (``None`` if unlimited)."""
        if self.limit is None:
            return None
        return max(0, self.limit - self.used)

    def would_exceed(self, amount: int) -> bool:
        """Return whether consuming ``amount`` more would exceed the limit."""
        if self.limit is None:
            return False
        return self.used + amount > self.limit


class Subscription(TenantScopedEntity):
    """A tenant's subscription and its live usage meters."""

    plan_tier: PlanTier = PlanTier.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    seats_purchased: int | None = 3
    period_start: datetime | None = None
    period_end: datetime | None = None
    usage: dict[str, UsageState] = Field(default_factory=dict)

    def meter(self, meter: Meter) -> UsageState:
        """Return the usage state for ``meter`` (zero/unlimited if unset)."""
        return self.usage.get(meter.value, UsageState(meter=meter))


@runtime_checkable
class BillingHook(Protocol):
    """Future billing seam — the platform notifies, a provider reacts."""

    def on_subscription_created(self, subscription: Subscription) -> None: ...
    def on_plan_changed(self, subscription: Subscription, previous: PlanTier) -> None: ...
    def on_usage_recorded(self, subscription: Subscription, meter: Meter, amount: int) -> None: ...


class NullBillingHook:
    """Default no-op billing hook (no payment integration)."""

    def on_subscription_created(self, subscription: Subscription) -> None:
        """Do nothing."""

    def on_plan_changed(self, subscription: Subscription, previous: PlanTier) -> None:
        """Do nothing."""

    def on_usage_recorded(self, subscription: Subscription, meter: Meter, amount: int) -> None:
        """Do nothing."""
