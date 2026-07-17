"""Platform Administration workspace (Phase 6 / Milestone 1 — Module 13).

An enterprise operations console for the platform team: organizations, users,
subscriptions, usage, licensing, features, audit events, system status, health
and configuration across every tenant.

The page is UI-only and fully offline. It drives a deterministic, pre-seeded
demo platform (:func:`build_demo_platform`), so it renders instantly with no
dataset, provider or network — and the AppTest stays fast. All logic lives in
``src/platform``; this module only presents it.
"""

from __future__ import annotations

import streamlit as st

from src.platform.demo import build_demo_platform
from src.platform.subscription import Meter

_PLATFORM_KEY = "platform_admin_instance"

# The platform modules and the human-facing status shown on the health board.
_MODULES = [
    ("Organizations", "organizations"),
    ("Multi-Tenancy", "tenants"),
    ("Authentication", "auth"),
    ("RBAC", "rbac"),
    ("Workspaces", "workspaces"),
    ("Configuration", "config"),
    ("Subscriptions", "subscriptions"),
    ("Notifications", "notifications"),
    ("Audit", "audit"),
    ("Storage", "storage"),
    ("Developer Platform", "extensions"),
]


def _get_platform():
    """Return the pre-seeded demo platform, cached for the session."""
    if _PLATFORM_KEY not in st.session_state:
        st.session_state[_PLATFORM_KEY] = build_demo_platform()
    return st.session_state[_PLATFORM_KEY]


def render_platform_admin() -> None:
    """Render the Platform Administration workspace."""
    st.title("🏛️ Platform Administration")
    st.caption(
        "Enterprise operations console — organizations, tenants, identity, "
        "access control, subscriptions, configuration, audit and system health "
        "for the entire TalentMind SaaS platform."
    )

    platform = _get_platform()
    orgs = platform.organizations.list_organizations()

    _render_kpis(platform, orgs)

    (
        tab_overview,
        tab_orgs,
        tab_users,
        tab_subs,
        tab_lic,
        tab_config,
        tab_audit,
    ) = st.tabs(
        [
            "📊 Overview & Health",
            "🏢 Organizations",
            "👥 Users",
            "💳 Subscriptions & Usage",
            "🔑 Licensing & Features",
            "⚙️ Configuration",
            "🧾 Audit Events",
        ]
    )

    with tab_overview:
        _render_overview(platform, orgs)
    with tab_orgs:
        _render_organizations(platform, orgs)
    with tab_users:
        _render_users(platform, orgs)
    with tab_subs:
        _render_subscriptions(platform, orgs)
    with tab_lic:
        _render_licensing(platform, orgs)
    with tab_config:
        _render_configuration(platform, orgs)
    with tab_audit:
        _render_audit(platform, orgs)


# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------


def _render_kpis(platform, orgs) -> None:
    """Render the top-line platform KPI metrics."""
    total_users = sum(platform.auth.users.count(tenant_id=o.id) for o in orgs)
    total_audit = sum(len(platform.audit.query(o.id)) for o in orgs)
    active_sessions = sum(
        len(
            [
                s
                for s in platform.auth.sessions_repo.list(tenant_id=o.id)
                if s.is_active_at(platform.clock.now())
            ]
        )
        for o in orgs
    )

    cols = st.columns(5)
    cols[0].metric("Organizations", len(orgs))
    cols[1].metric("Tenants", len(platform.tenants.list()))
    cols[2].metric("Users", total_users)
    cols[3].metric("Active sessions", active_sessions)
    cols[4].metric("Audit events", total_audit)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def _render_overview(platform, orgs) -> None:
    """Render system status, module health and audit-chain integrity."""
    st.subheader("System Status")
    st.success("All platform modules operational · offline reference deployment")

    st.markdown("#### Module Health")
    health_rows = [
        {"module": label, "status": "🟢 healthy", "registered": platform.container.has(key)}
        for label, key in _MODULES
    ]
    st.dataframe(health_rows, use_container_width=True, hide_index=True)

    st.markdown("#### Tenant Health & Audit Integrity")
    rows = []
    for org in orgs:
        rows.append(
            {
                "organization": org.display_name,
                "status": org.status.value,
                "tenant": org.id,
                "audit_chain": "✅ intact" if platform.audit.verify_chain(org.id) else "❌ broken",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    stats = platform.tenants.cache.stats
    st.caption(
        f"Tenant cache — hits: {stats['hits']} · misses: {stats['misses']} · "
        f"entries: {stats['size']}"
    )


def _render_organizations(platform, orgs) -> None:
    """Render the organization directory and hierarchy summary."""
    st.subheader("Organizations")
    rows = []
    for org in orgs:
        rows.append(
            {
                "name": org.display_name,
                "slug": org.slug,
                "status": org.status.value,
                "region": org.settings.data_region,
                "max_users": org.limits.max_users,
                "max_workspaces": org.limits.max_workspaces,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_users(platform, orgs) -> None:
    """Render users across tenants with their role assignments."""
    st.subheader("Users & Roles")
    rows = []
    for org in orgs:
        for user in platform.auth.users.list(tenant_id=org.id):
            assignments = platform.access_control.assignments_for(org.id, user.id)
            roles = ", ".join(sorted({a.role for a in assignments})) or "—"
            rows.append(
                {
                    "organization": org.slug,
                    "user": user.display_name or user.email,
                    "email": user.email,
                    "status": user.status.value,
                    "verified": "✅" if user.email_verified else "—",
                    "roles": roles,
                }
            )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_subscriptions(platform, orgs) -> None:
    """Render subscription plans and metered usage with progress bars."""
    st.subheader("Subscriptions & Usage")
    for org in orgs:
        sub = platform.subscriptions.get(org.id)
        if sub is None:
            continue
        st.markdown(f"**{org.display_name}** — `{sub.plan_tier.value}` plan")
        cols = st.columns(4)
        for i, meter in enumerate(
            [Meter.SEATS, Meter.AI_CREDITS, Meter.STORAGE_GB, Meter.API_REQUESTS]
        ):
            state = sub.meter(meter)
            limit_label = "∞" if state.limit is None else str(state.limit)
            cols[i].metric(meter.value, f"{state.used} / {limit_label}")
            if state.limit:
                cols[i].progress(min(1.0, state.used / state.limit))
        st.divider()


def _render_licensing(platform, orgs) -> None:
    """Render license status and enabled feature flags per organization."""
    st.subheader("Licensing")
    lic_rows = []
    for org in orgs:
        config = platform.config.get(org.id)
        if config is None:
            continue
        lic = config.license
        lic_rows.append(
            {
                "organization": org.slug,
                "plan": lic.plan,
                "status": lic.status.value,
                "seats": lic.seats,
                "entitlements": ", ".join(lic.entitlements) or "—",
            }
        )
    st.dataframe(lic_rows, use_container_width=True, hide_index=True)

    st.subheader("Feature Flags")
    feat_rows = []
    for org in orgs:
        config = platform.config.get(org.id)
        if config is None:
            continue
        for key, enabled in config.feature_flags.items():
            feat_rows.append(
                {
                    "organization": org.slug,
                    "feature": key,
                    "enabled": "🟢 on" if enabled else "⚪ off",
                }
            )
    if feat_rows:
        st.dataframe(feat_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No feature flags configured.")


def _render_configuration(platform, orgs) -> None:
    """Render localization, regional and AI configuration per organization."""
    st.subheader("Configuration")
    rows = []
    for org in orgs:
        config = platform.config.get(org.id)
        if config is None:
            continue
        rows.append(
            {
                "organization": org.slug,
                "language": config.localization.language,
                "locale": config.localization.locale,
                "timezone": config.regional.timezone,
                "region": config.regional.region,
                "currency": config.localization.currency,
                "ai_provider": config.ai_provider.provider,
                "model": config.model.model,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_audit(platform, orgs) -> None:
    """Render the most recent platform audit events across tenants."""
    st.subheader("Audit Events")
    org_by_id = {o.id: o for o in orgs}
    events = []
    for org in orgs:
        events.extend(platform.audit.query(org.id))
    events.sort(key=lambda e: e.created_at, reverse=True)

    rows = [
        {
            "time": e.created_at.strftime("%Y-%m-%d %H:%M"),
            "organization": org_by_id[e.tenant_id].slug
            if e.tenant_id in org_by_id
            else e.tenant_id,
            "category": e.category.value,
            "action": e.action,
            "actor": e.actor_id,
            "outcome": e.outcome.value,
        }
        for e in events[:100]
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(f"{len(events)} total audit events · newest 100 shown")
