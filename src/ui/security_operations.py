"""Security & Operations Center workspace (Phase 6 / Milestone 4 — Module 10).

An enterprise security & operations console: platform health, security status,
audit timeline, alerts, policy violations, threat events, compliance status,
observability metrics and a system overview.

The page is UI-only and fully offline. It drives a deterministic, pre-seeded
demo security platform (:func:`build_security_demo`), so it renders instantly
with no dataset, provider or network — and the AppTest stays fast. All logic
lives in ``src/platform/security``; this module only presents it.
"""

from __future__ import annotations

import streamlit as st

from src.platform.security.compliance.models import ComplianceStandard
from src.platform.security.demo import build_security_demo

_PLATFORM_KEY = "security_ops_instance"
_TENANT = "org_acme"
_ORG = "org_acme"


def _get_platform():
    """Return the pre-seeded demo security platform, cached for the session."""
    if _PLATFORM_KEY not in st.session_state:
        st.session_state[_PLATFORM_KEY] = build_security_demo()
    return st.session_state[_PLATFORM_KEY]


def render_security_operations() -> None:
    """Render the Security & Operations Center workspace."""
    st.title("🛡️ Security & Operations Center")
    st.caption(
        "Enterprise security, governance, compliance and observability — "
        "identity, audit, secrets, monitoring, threats, policy and incidents "
        "for the TalentMind platform. Deterministic and offline by default."
    )

    sp = _get_platform()
    _render_kpis(sp)

    (
        tab_overview,
        tab_audit,
        tab_alerts,
        tab_threats,
        tab_policy,
        tab_compliance,
        tab_incidents,
    ) = st.tabs(
        [
            "📊 System Overview",
            "🧾 Audit Timeline",
            "🚨 Alerts",
            "🕵️ Threat Events",
            "📜 Policy & Governance",
            "✅ Compliance Status",
            "🔥 Incidents",
        ]
    )

    with tab_overview:
        _render_overview(sp)
    with tab_audit:
        _render_audit(sp)
    with tab_alerts:
        _render_alerts(sp)
    with tab_threats:
        _render_threats(sp)
    with tab_policy:
        _render_policy(sp)
    with tab_compliance:
        _render_compliance(sp)
    with tab_incidents:
        _render_incidents(sp)


# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------


def _render_kpis(sp) -> None:
    """Render top-line security KPIs."""
    threat = sp.threat.threat_report(_TENANT, _ORG)
    alerts = sp.monitoring.active_alerts(_TENANT)
    incidents = sp.incidents.report(_TENANT)

    cols = st.columns(5)
    cols[0].metric("Identities", len(sp.identity.list(_TENANT)))
    cols[1].metric("Audit entries", sp.audit.count(_TENANT))
    cols[2].metric("Active alerts", len(alerts))
    cols[3].metric("Threat events", threat.total_events)
    cols[4].metric("Open incidents", incidents["open"])


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def _render_overview(sp) -> None:
    """Render the system overview / security status."""
    st.subheader("System Overview")
    threat = sp.threat.threat_report(_TENANT, _ORG)
    banner = {
        "none": st.success,
        "low": st.success,
        "medium": st.warning,
        "high": st.error,
        "critical": st.error,
    }.get(threat.highest_risk.value, st.info)
    banner(f"Security status — highest active risk: {threat.highest_risk.value.upper()}")

    st.markdown("#### Platform Health & Status")
    rows = [
        {
            "component": "Identity",
            "status": "🟢 operational",
            "detail": f"{len(sp.identity.list(_TENANT))} identities",
        },
        {
            "component": "Audit chain",
            "status": "✅ intact" if sp.audit.verify_chain(_TENANT) else "❌ broken",
            "detail": f"{sp.audit.count(_TENANT)} entries",
        },
        {
            "component": "Secrets",
            "status": "🟢 operational",
            "detail": f"{len(sp.secrets.metadata(_TENANT))} managed",
        },
        {
            "component": "Monitoring",
            "status": "🟢 operational",
            "detail": f"{len(sp.monitoring.rules_for(_TENANT))} rules",
        },
        {
            "component": "Governance",
            "status": "🟢 operational",
            "detail": f"{len(sp.governance.policies_for(_TENANT))} policies",
        },
        {
            "component": "Threat detection",
            "status": "🟢 operational",
            "detail": f"{threat.total_events} events",
        },
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("#### Observability Metrics")
    dash = sp.analytics.executive_dashboard(_TENANT, _ORG)
    st.json(dash)


def _render_audit(sp) -> None:
    """Render the central audit timeline."""
    st.subheader("Audit Timeline")
    entries = sp.audit.search(_TENANT, limit=200)
    rows = [
        {
            "seq": e.sequence,
            "type": e.event_type.value,
            "action": e.action,
            "actor": e.actor_id,
            "outcome": e.outcome.value,
            "correlation": e.correlation_id[:12],
        }
        for e in entries
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        f"{sp.audit.count(_TENANT)} immutable entries · chain "
        + ("✅ intact" if sp.audit.verify_chain(_TENANT) else "❌ broken")
    )


def _render_alerts(sp) -> None:
    """Render monitoring alerts."""
    st.subheader("Alerts")
    alerts = sp.monitoring.all_alerts(_TENANT)
    rows = [
        {
            "name": a.name,
            "domain": a.domain.value,
            "severity": a.severity.value,
            "metric": a.metric,
            "value": a.value,
            "threshold": a.threshold,
            "resolved": "✅" if a.resolved else "—",
        }
        for a in alerts
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts raised.")


def _render_threats(sp) -> None:
    """Render threat events and the threat report."""
    st.subheader("Threat Events")
    report = sp.threat.threat_report(_TENANT, _ORG)
    cols = st.columns(3)
    cols[0].metric("Total events", report.total_events)
    cols[1].metric("Unresolved", report.unresolved)
    cols[2].metric("Highest risk", report.highest_risk.value)
    rows = [
        {
            "type": e.threat_type.value,
            "risk": e.risk_level.value,
            "actor": e.actor_id or "—",
            "description": e.description,
            "resolved": "✅" if e.resolved else "—",
        }
        for e in sp.threat.list_events(_TENANT)
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_policy(sp) -> None:
    """Render governance policies and configuration change history."""
    st.subheader("Policy & Governance")
    rows = [
        {
            "policy": p.name,
            "domain": p.domain.value,
            "enforcement": p.enforcement.value,
            "rules": len(p.rules),
            "enabled": "🟢" if p.enabled else "⚪",
        }
        for p in sp.governance.policies_for(_TENANT)
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.markdown("#### Configuration Changes")
    try:
        history = sp.configuration.history(_TENANT, "session_timeout_minutes")
        st.dataframe(
            [{"version": v.version, "value": v.value, "note": v.note} for v in history],
            use_container_width=True,
            hide_index=True,
        )
    except Exception:
        st.info("No configuration entries.")


def _render_compliance(sp) -> None:
    """Render compliance coverage across standards."""
    st.subheader("Compliance Status")
    rows = []
    for standard in ComplianceStandard:
        report = sp.compliance.assess(_TENANT, standard)
        rows.append(
            {
                "standard": standard.value.upper(),
                "controls": report.total_controls,
                "satisfied": report.satisfied,
                "partial": report.partial,
                "unsatisfied": report.unsatisfied,
                "coverage": f"{report.coverage * 100:.0f}%",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_incidents(sp) -> None:
    """Render incidents and the incident report."""
    st.subheader("Incidents")
    report = sp.incidents.report(_TENANT)
    cols = st.columns(3)
    cols[0].metric("Total", report["total"])
    cols[1].metric("Open", report["open"])
    cols[2].metric("Escalated", report["escalated"])
    rows = [
        {
            "title": i.title,
            "severity": i.severity.value,
            "status": i.status.value,
            "owner": i.owner or "—",
            "root_cause": i.root_cause or "—",
        }
        for i in sp.incidents.list(_TENANT)
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
