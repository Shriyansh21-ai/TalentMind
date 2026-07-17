"""Integration Marketplace workspace (Phase 6 / Milestone 2 — Module 11).

An enterprise integration console: browse the available-provider marketplace,
review a tenant's installed integrations, their connection status, health,
capabilities, configuration, logs, and sync/webhook status — plus the event bus
and developer SDK foundation.

The page is UI-only and fully offline. It drives a deterministic, pre-seeded
demo integration platform (:func:`build_integration_demo`), so it renders
instantly with no dataset, provider or network — and the AppTest stays fast. All
logic lives in ``src/platform/integrations``; this module only presents it.
"""

from __future__ import annotations

import streamlit as st

from src.platform.integrations.common.models import ProviderCategory
from src.platform.integrations.demo import build_integration_demo
from src.platform.integrations.sdk import sdk_catalog

_PLATFORM_KEY = "integration_platform_instance"

# Demo tenants seeded by build_integration_demo (slug shown in the UI).
_TENANTS = [("Acme Corporation", "org_acme"), ("Globex LLC", "org_globex")]


def _get_platform():
    """Return the pre-seeded demo integration platform, cached for the session."""
    if _PLATFORM_KEY not in st.session_state:
        st.session_state[_PLATFORM_KEY] = build_integration_demo()
    return st.session_state[_PLATFORM_KEY]


def render_integration_marketplace() -> None:
    """Render the Integration Marketplace workspace."""
    st.title("Integration Marketplace")
    st.caption(
        "Enterprise integration platform — HRIS, ATS, calendar, communication "
        "and document providers, API gateway, webhooks, event bus and "
        "synchronization. Offline by default; every provider is swappable."
    )

    platform = _get_platform()
    _render_kpis(platform)

    (
        tab_market,
        tab_installed,
        tab_health,
        tab_webhooks,
        tab_events,
        tab_sdk,
    ) = st.tabs(
        [
            "Marketplace",
            "Installed",
            "Health & Logs",
            "Webhooks & Sync",
            "Event Bus",
            "Developer SDKs",
        ]
    )

    with tab_market:
        _render_marketplace(platform)
    with tab_installed:
        _render_installed(platform)
    with tab_health:
        _render_health(platform)
    with tab_webhooks:
        _render_webhooks_sync(platform)
    with tab_events:
        _render_events(platform)
    with tab_sdk:
        _render_sdks(platform)


# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------


def _render_kpis(platform) -> None:
    """Render top-line integration KPIs across demo tenants."""
    catalog = platform.registry.definitions()
    installed = sum(len(platform.manager.list(t_id)) for _n, t_id in _TENANTS)
    connected = sum(
        1 for _n, t_id in _TENANTS for i in platform.manager.list(t_id) if i.is_connected
    )
    total_events = len(platform.events.history())

    cols = st.columns(5)
    cols[0].metric("Available providers", len(catalog))
    cols[1].metric("Provider families", len(platform.registry.categories()))
    cols[2].metric("Installed", installed)
    cols[3].metric("Connected", connected)
    cols[4].metric("Events published", total_events)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def _render_marketplace(platform) -> None:
    """Render the available-provider catalogue grouped by category."""
    st.subheader("Available Providers")
    st.success(
        f"{len(platform.registry.definitions())} providers across "
        f"{len(platform.registry.categories())} families · offline reference "
        "catalogue — no live connections"
    )
    for category in ProviderCategory:
        definitions = platform.registry.definitions(category=category)
        if not definitions:
            continue
        st.markdown(f"#### {category.value.upper()} ({len(definitions)})")
        rows = [
            {
                "provider": d.metadata.display_name,
                "vendor": d.metadata.vendor,
                "auth": ", ".join(a.value for a in d.metadata.auth_schemes),
                "sync": "Yes" if d.capabilities.supports_incremental_sync else "—",
                "webhooks": "Yes" if d.capabilities.supports_webhooks else "—",
                "write": "Yes" if d.capabilities.supports_write else "—",
            }
            for d in definitions
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_installed(platform) -> None:
    """Render each tenant's installed integrations and their status."""
    st.subheader("Installed Integrations")
    for name, tenant_id in _TENANTS:
        integrations = platform.manager.list(tenant_id)
        st.markdown(f"**{name}** — {len(integrations)} installed")
        rows = [
            {
                "integration": i.display_name,
                "category": i.category.value,
                "status": i.status.value,
                "health": i.health.state.value,
                "credential": platform.manager.credential_preview(tenant_id, i.id),
                "sync": "on" if i.configuration.sync_enabled else "off",
                "webhooks": "on" if i.configuration.webhook_enabled else "off",
            }
            for i in integrations
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.divider()


def _render_health(platform) -> None:
    """Render per-integration health, statistics and recent logs."""
    st.subheader("Health, Statistics & Logs")
    for name, tenant_id in _TENANTS:
        for integration in platform.manager.list(tenant_id):
            detail = platform.marketplace.detail(tenant_id, integration.id)
            stats = detail.statistics
            with st.expander(
                f"{name} · {integration.display_name} — {integration.health.state.value}"
            ):
                cols = st.columns(4)
                cols[0].metric("Status", integration.status.value)
                cols[1].metric("Connect attempts", stats.connect_attempts if stats else 0)
                cols[2].metric(
                    "Success rate",
                    f"{(stats.success_rate * 100):.0f}%" if stats else "—",
                )
                cols[3].metric(
                    "Sync records",
                    detail.sync_health.get("records_processed", 0),
                )
                caps = detail.definition.capabilities
                st.caption(
                    "Capabilities: "
                    + ", ".join(
                        c
                        for c, on in [
                            ("read", caps.supports_read),
                            ("write", caps.supports_write),
                            ("incremental-sync", caps.supports_incremental_sync),
                            ("webhooks", caps.supports_webhooks),
                            ("realtime", caps.supports_realtime),
                        ]
                        if on
                    )
                )
                log_rows = [
                    {"event": e.event, "level": e.level.value, "detail": e.message}
                    for e in detail.logs
                ]
                if log_rows:
                    st.dataframe(log_rows, use_container_width=True, hide_index=True)


def _render_webhooks_sync(platform) -> None:
    """Render webhook subscriptions/deliveries and sync jobs per tenant."""
    st.subheader("Webhooks")
    for name, tenant_id in _TENANTS:
        subs = platform.webhooks.subscriptions(tenant_id)
        deliveries = platform.webhooks.deliveries(tenant_id)
        st.markdown(f"**{name}** — {len(subs)} subscriptions · {len(deliveries)} deliveries")
        rows = [
            {
                "url": s.url,
                "direction": s.direction.value,
                "filters": ", ".join(s.event_filters),
                "active": "Yes" if s.active else "—",
            }
            for s in subs
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Synchronization")
    for name, tenant_id in _TENANTS:
        jobs = platform.sync.jobs(tenant_id)
        rows = [
            {
                "integration": j.integration_id,
                "mode": j.mode.value,
                "state": j.state.value,
                "processed": j.records_processed,
                "conflicts": len(j.conflicts),
                "unresolved": j.unresolved_conflicts,
            }
            for j in jobs
        ]
        st.markdown(f"**{name}** — {len(jobs)} sync jobs")
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_events(platform) -> None:
    """Render the enterprise event bus log and any dead letters."""
    st.subheader("Enterprise Event Bus")
    events = platform.events.history()
    st.caption(
        f"{len(events)} events · {len(platform.events.subscriptions())} "
        f"subscriptions · {len(platform.events.dead_letters())} dead letters"
    )
    rows = [
        {
            "seq": e.sequence,
            "topic": e.topic,
            "type": e.event_type.value,
            "tenant": e.tenant_id or "—",
        }
        for e in sorted(events, key=lambda e: e.sequence, reverse=True)[:100]
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No events published yet.")


def _render_sdks(platform) -> None:
    """Render the developer SDK foundation catalogue."""
    st.subheader("Developer SDK Foundation")
    st.caption("Planned package structure — future SDKs, no code shipped yet.")
    rows = [
        {
            "sdk": s.name,
            "package": s.package,
            "language": s.language,
            "modules": ", ".join(s.modules),
            "status": s.status,
        }
        for s in sdk_catalog()
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
