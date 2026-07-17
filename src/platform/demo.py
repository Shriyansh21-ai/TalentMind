"""Offline demo fixture for the Platform Administration workspace (Module 13).

Builds a fully-wired :class:`Platform` pre-seeded with a handful of
organizations, users, role grants, subscriptions, feature flags and audit
events. Everything is offline and deterministic (a :class:`FrozenClock` drives
time), so the platform dashboard and its AppTest render instantly with no
dataset, provider or network.
"""

from __future__ import annotations

from src.platform.audit import AuditCategory, AuditOutcome
from src.platform.bootstrap import Platform, build_platform
from src.platform.common.clock import FrozenClock
from src.platform.config import License, LicenseStatus
from src.platform.rbac import Role
from src.platform.subscription import Meter, PlanTier

# (legal_name, slug, plan, seat_users) — deterministic seed data.
_SEED = [
    ("Acme Corporation", "acme", PlanTier.ENTERPRISE, ["ceo", "hr.director", "recruiter.a"]),
    ("Globex LLC", "globex", PlanTier.BUSINESS, ["admin", "recruiter.b"]),
    ("Initech Inc", "initech", PlanTier.PROFESSIONAL, ["hiring.mgr"]),
    ("Umbrella Group", "umbrella", PlanTier.FREE, ["viewer"]),
]

_ROLE_BY_LOCAL = {
    "ceo": Role.EXECUTIVE,
    "hr.director": Role.HR_DIRECTOR,
    "recruiter.a": Role.RECRUITER,
    "recruiter.b": Role.RECRUITER,
    "admin": Role.ORGANIZATION_ADMIN,
    "hiring.mgr": Role.HIRING_MANAGER,
    "viewer": Role.VIEWER,
}


def build_demo_platform() -> Platform:
    """Return a :class:`Platform` seeded with deterministic demo tenants."""
    platform = build_platform(clock=FrozenClock())

    for legal_name, slug, plan, seats in _SEED:
        org, _tenant = platform.provision_organization(legal_name, slug=slug, plan=plan)

        # A couple of feature flags + a license per org.
        platform.config.set_feature(org.id, "ai_copilot", True)
        platform.config.set_feature(org.id, "beta_dashboards", plan != PlanTier.FREE)
        platform.config.set_license(
            org.id,
            License(
                plan=plan.value,
                seats=len(seats),
                status=LicenseStatus.ACTIVE,
                entitlements=["ai_copilot", "audit_export"]
                if plan != PlanTier.FREE
                else ["ai_copilot"],
            ),
        )

        # Users, role grants, seat allocation + a login audit event each.
        for local in seats:
            email = f"{local}@{slug}.com"
            user = platform.auth.register_user(
                org.id, org.id, email, "Sup3rSecret!!42", display_name=local
            )
            platform.access_control.assign(
                org.id, org.id, user.id, _ROLE_BY_LOCAL.get(local, Role.VIEWER)
            )
            try:
                platform.subscriptions.allocate_seat(org.id)
            except Exception:  # unlimited plans never raise; free plan may cap
                pass
            platform.auth.login(org.id, org.id, email, "Sup3rSecret!!42")
            platform.audit.record(
                org.id,
                org.id,
                AuditCategory.AUTHENTICATION,
                "user.login",
                actor_id=user.id,
                target_type="user",
                target_id=user.id,
                outcome=AuditOutcome.SUCCESS,
            )

        # A little metered AI usage for the dashboard.
        try:
            platform.subscriptions.record_usage(org.id, Meter.AI_CREDITS, 250)
        except Exception:
            pass

    return platform
