"""Subscription plan catalogue (Module 7).

The five plan tiers and their entitlements. Prices are indicative only — there
is **no payment integration**; this is the architecture a future billing system
binds to via :class:`~src.platform.subscription.models.BillingHook`.
"""

from __future__ import annotations

from enum import Enum

from src.platform.common.models import PlatformModel


class PlanTier(str, Enum):
    """The available subscription tiers."""

    FREE = "free"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class PlanDefinition(PlatformModel):
    """The entitlements and limits conferred by a plan tier.

    ``None`` for a numeric limit means "unlimited" (typical for Enterprise /
    Custom). ``entitlements`` are feature keys the configuration/RBAC layers can
    gate on.
    """

    tier: PlanTier
    name: str
    monthly_price_usd: float | None = 0.0
    included_seats: int | None = 3
    ai_credits_monthly: int | None = 1_000
    storage_gb: int | None = 5
    api_requests_per_minute: int | None = 60
    entitlements: list[str] = []


PLAN_CATALOG: dict[PlanTier, PlanDefinition] = {
    PlanTier.FREE: PlanDefinition(
        tier=PlanTier.FREE,
        name="Free",
        monthly_price_usd=0.0,
        included_seats=3,
        ai_credits_monthly=1_000,
        storage_gb=5,
        api_requests_per_minute=60,
        entitlements=["ai_copilot"],
    ),
    PlanTier.PROFESSIONAL: PlanDefinition(
        tier=PlanTier.PROFESSIONAL,
        name="Professional",
        monthly_price_usd=99.0,
        included_seats=10,
        ai_credits_monthly=25_000,
        storage_gb=50,
        api_requests_per_minute=300,
        entitlements=["ai_copilot", "api_access", "custom_branding"],
    ),
    PlanTier.BUSINESS: PlanDefinition(
        tier=PlanTier.BUSINESS,
        name="Business",
        monthly_price_usd=499.0,
        included_seats=50,
        ai_credits_monthly=250_000,
        storage_gb=500,
        api_requests_per_minute=1_200,
        entitlements=[
            "ai_copilot",
            "api_access",
            "custom_branding",
            "advanced_rbac",
            "audit_export",
        ],
    ),
    PlanTier.ENTERPRISE: PlanDefinition(
        tier=PlanTier.ENTERPRISE,
        name="Enterprise",
        monthly_price_usd=None,  # custom-negotiated
        included_seats=None,
        ai_credits_monthly=None,
        storage_gb=None,
        api_requests_per_minute=None,
        entitlements=[
            "ai_copilot",
            "api_access",
            "custom_branding",
            "advanced_rbac",
            "audit_export",
            "sso",
            "scim_provisioning",
        ],
    ),
    PlanTier.CUSTOM: PlanDefinition(
        tier=PlanTier.CUSTOM,
        name="Custom",
        monthly_price_usd=None,
        included_seats=None,
        ai_credits_monthly=None,
        storage_gb=None,
        api_requests_per_minute=None,
        entitlements=[],
    ),
}


def plan_for(tier: PlanTier | str) -> PlanDefinition:
    """Return the :class:`PlanDefinition` for a tier (defaults to Free)."""
    if isinstance(tier, str):
        try:
            tier = PlanTier(tier)
        except ValueError:
            tier = PlanTier.FREE
    return PLAN_CATALOG[tier]
