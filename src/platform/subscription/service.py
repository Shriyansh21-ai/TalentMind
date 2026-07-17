"""Subscription service (Module 7).

Subscribes tenants to plans, seeds usage meters from the plan's limits, records
metered usage with quota enforcement, and handles plan changes — emitting
events to a :class:`BillingHook` at every billing-relevant moment so a future
payment provider can bind in without any change here.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import ConflictError, QuotaExceededError
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.subscription.models import (
    BillingHook,
    Meter,
    NullBillingHook,
    Subscription,
    SubscriptionStatus,
    UsageState,
)
from src.platform.subscription.plans import PlanDefinition, PlanTier, plan_for


class SubscriptionService:
    """Manage tenant subscriptions, plans and metered usage."""

    def __init__(
        self,
        *,
        repository: InMemoryRepository[Subscription] | None = None,
        billing_hook: BillingHook | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.repo = repository or InMemoryRepository("subscription")
        self._billing = billing_hook or NullBillingHook()
        self._clock = clock or SystemClock()

    # -- lifecycle ----------------------------------------------------------

    def subscribe(
        self,
        tenant_id: str,
        organization_id: str,
        tier: PlanTier | str = PlanTier.FREE,
    ) -> Subscription:
        """Create the tenant's subscription for ``tier`` and seed its meters.

        Raises:
            ConflictError: If the tenant already has a subscription.
        """
        if self.repo.list(tenant_id=tenant_id):
            raise ConflictError(f"tenant '{tenant_id}' already has a subscription")
        plan = plan_for(tier)
        now = self._clock.now()
        subscription = Subscription(
            id=generate_id("sub"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            plan_tier=plan.tier,
            status=SubscriptionStatus.ACTIVE,
            seats_purchased=plan.included_seats,
            period_start=now,
            usage=self._seed_meters(plan),
            created_at=now,
            updated_at=now,
        )
        self.repo.add(subscription)
        self._billing.on_subscription_created(subscription)
        return subscription

    @staticmethod
    def _seed_meters(plan: PlanDefinition) -> dict[str, UsageState]:
        """Build zeroed usage meters from a plan's limits."""
        return {
            Meter.SEATS.value: UsageState(meter=Meter.SEATS, limit=plan.included_seats),
            Meter.AI_CREDITS.value: UsageState(
                meter=Meter.AI_CREDITS, limit=plan.ai_credits_monthly
            ),
            Meter.STORAGE_GB.value: UsageState(meter=Meter.STORAGE_GB, limit=plan.storage_gb),
            Meter.API_REQUESTS.value: UsageState(
                meter=Meter.API_REQUESTS, limit=plan.api_requests_per_minute
            ),
        }

    def get(self, tenant_id: str) -> Subscription | None:
        """Return the tenant's subscription (or ``None``)."""
        found = self.repo.list(tenant_id=tenant_id)
        return found[0] if found else None

    def require(self, tenant_id: str) -> Subscription:
        """Return the tenant's subscription or raise :class:`NotFoundError`."""
        sub = self.get(tenant_id)
        if sub is None:
            from src.platform.common.errors import NotFoundError

            raise NotFoundError(f"no subscription for tenant '{tenant_id}'")
        return sub

    def change_plan(self, tenant_id: str, tier: PlanTier | str) -> Subscription:
        """Move a tenant to a new plan, re-seeding limits (usage preserved)."""
        sub = self.require(tenant_id)
        previous = sub.plan_tier
        plan = plan_for(tier)
        sub.plan_tier = plan.tier
        sub.seats_purchased = plan.included_seats
        # Preserve used counters, adopt new limits.
        seeded = self._seed_meters(plan)
        for key, state in seeded.items():
            state.used = sub.usage.get(key, state).used
        sub.usage = seeded
        sub.touch(self._clock.now())
        self.repo.update(sub)
        self._billing.on_plan_changed(sub, previous)
        return sub

    # -- metered usage ------------------------------------------------------

    def record_usage(self, tenant_id: str, meter: Meter, amount: int = 1) -> Subscription:
        """Record ``amount`` of usage on ``meter``, enforcing the quota.

        Raises:
            QuotaExceededError: If recording would exceed the meter's limit.
        """
        sub = self.require(tenant_id)
        state = sub.usage.get(meter.value, UsageState(meter=meter))
        if state.would_exceed(amount):
            raise QuotaExceededError(
                f"{meter.value} quota exceeded ({state.used}+{amount} > {state.limit})"
            )
        state.used += amount
        sub.usage = {**sub.usage, meter.value: state}
        sub.touch(self._clock.now())
        self.repo.update(sub)
        self._billing.on_usage_recorded(sub, meter, amount)
        return sub

    def remaining(self, tenant_id: str, meter: Meter) -> int | None:
        """Return remaining allowance on a meter (``None`` if unlimited)."""
        return self.require(tenant_id).meter(meter).remaining()

    def allocate_seat(self, tenant_id: str) -> Subscription:
        """Consume one seat (enforces the seat quota)."""
        return self.record_usage(tenant_id, Meter.SEATS, 1)

    def release_seat(self, tenant_id: str) -> Subscription:
        """Release one seat (never drops below zero)."""
        sub = self.require(tenant_id)
        state = sub.usage.get(Meter.SEATS.value, UsageState(meter=Meter.SEATS))
        state.used = max(0, state.used - 1)
        sub.usage = {**sub.usage, Meter.SEATS.value: state}
        sub.touch(self._clock.now())
        return self.repo.update(sub)
