"""Enterprise Hiring Intelligence & Workforce Analytics workspace (Modules 10, 11, 12).

A professional, board-ready workspace that renders the unified
:class:`HiringIntelligenceReport`: hiring health, executive KPIs, cohort
distributions, pipeline bottlenecks, team analytics, trends, capacity, forecast,
benchmarks, optimization opportunities and an enterprise dashboard.

Presentation only — all reasoning comes from :class:`HiringIntelligenceEngine`,
which aggregates existing per-candidate intelligence into organizational analytics
(never candidate ranking), marks unavailable metrics honestly and fabricates no
enterprise statistics. This is an ORGANIZATION-level workspace (no candidate picker).
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

import streamlit as st

from src.ai.core.runner import AgentRunner
from src.ai.agents.hiring_intelligence.analytics_engine import HiringIntelligenceEngine
from src.ai.agents.hiring_intelligence.schemas import HiringIntelligenceReport
from src.ai.agents.hiring_intelligence.templates import ANALYTICS_COHORT

_runner: Optional[AgentRunner] = None
_engine: Optional[HiringIntelligenceEngine] = None


def _get_engine(insights_fn=None) -> HiringIntelligenceEngine:
    """Return a shared workforce-intelligence engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = HiringIntelligenceEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_hiring_intelligence(
    candidates: List[Any],
    *,
    jd: str = "",
    insights_fn=None,
    generated_on: str = "",
    limit: int = ANALYTICS_COHORT,
    key_prefix: str = "hi",
) -> None:
    """Analyze a cohort and render the workforce-intelligence workspace."""
    st.subheader("📈 Enterprise Hiring Intelligence & Workforce Analytics")
    st.caption(
        "Strategic organizational intelligence — how healthy is our hiring "
        "organization, where are the bottlenecks, which teams hire well, and how "
        "future hiring can improve. It aggregates the platform's existing "
        "intelligence (never candidate ranking), marks unavailable metrics honestly "
        "and fabricates no enterprise statistics."
    )

    with st.spinner("Aggregating workforce hiring intelligence…"):
        engine = _get_engine(insights_fn)
        report = engine.build(candidates=candidates, jd=jd, limit=limit, generated_on=generated_on)

    _render_report(report, key_prefix=key_prefix)


_REGISTER_BADGE = {
    "Observed": "✅", "Estimated": "≈", "Forecast": "🔮", "Unavailable": "➖",
    "Recommendation": "💡", "Human Review": "👤",
}


def _badge(register: str) -> str:
    return _REGISTER_BADGE.get(register, "•")


def _render_report(report: HiringIntelligenceReport, *, key_prefix: str) -> None:
    """Render a full :class:`HiringIntelligenceReport`."""
    narrative = report.narrative
    health = next((k for k in report.kpis if k.name == "Hiring Health Index"), None)

    top = st.columns(4)
    top[0].metric("Analyzed Cohort", report.cohort_size)
    top[1].metric("Hiring Health", health.label if health else "n/a")
    top[2].metric("Priority Optimizations", sum(1 for o in report.optimizations if o.priority in ("Critical", "High")))
    top[3].metric("Analytics Source", "Connected" if report.data_available else "Not connected")

    if not report.data_available:
        st.info("ℹ️ No workforce-analytics source connected — trends, delays, team breakdowns and capacity are Unavailable and marked as such (Module 15). Analytics run over a bounded analyzed cohort.")
    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "📄 Summary",
            "📊 KPIs",
            "🥧 Distributions",
            "🚧 Bottlenecks",
            "🏢 Teams",
            "📉 Trends",
            "🧑‍🤝‍🧑 Capacity",
            "🔮 Forecast",
            "⚖️ Benchmarks",
            "💡 Optimization",
            "📈 Dashboard",
        ]
    )

    with tabs[0]:
        st.info(narrative.executive_summary)
        st.caption("🔎 " + narrative.data_availability_note)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Key insights**"); _bullets(narrative.key_insights, "")
            st.markdown("**Strategic recommendations**"); _bullets(narrative.strategic_recommendations, "")
        with c[1]:
            st.markdown("**Assumptions**"); _bullets(narrative.assumptions, "")
        st.caption("📌 " + narrative.confidence_note)

    with tabs[1]:
        st.caption(narrative.kpi_note)
        for k in report.kpis:
            val = f"{k.value:.0f}/100" if isinstance(k.value, (int, float)) else "n/a"
            st.markdown(f"{_badge(k.register)} **{k.name}** — {k.label} ({val})  _({k.register})_")
            if k.basis:
                st.caption(k.basis)

    with tabs[2]:
        for d in report.distributions:
            st.markdown(f"**{d.name}**  _({d.register})_")
            _bar(d.counts)
            if d.note:
                st.caption(d.note)

    with tabs[3]:
        st.caption(narrative.pipeline_note)
        for b in report.bottlenecks:
            st.markdown(f"{_badge(b.register)} **{b.stage}** — {b.severity}  _({b.register})_")
            if b.potential_cause:
                st.caption("Cause: " + b.potential_cause)
            if b.improvement:
                st.caption("Improvement: " + b.improvement)

    with tabs[4]:
        observed = [t for t in report.team_metrics if t.register == "Observed"]
        unavailable = [t for t in report.team_metrics if t.register == "Unavailable"]
        for t in observed:
            st.markdown(f"✅ **{t.dimension}: {t.group}** — {t.hiring_health}")
            st.caption(t.detail)
        if unavailable:
            st.caption("Unavailable dimensions (need org-structure data): " + ", ".join(sorted({t.dimension for t in unavailable})))

    with tabs[5]:
        st.caption(narrative.trend_note)
        for t in report.trends:
            st.markdown(f"{_badge(t.register)} **{t.name}** — {t.direction}")
            st.caption(t.evidence)

    with tabs[6]:
        st.caption(narrative.capacity_note)
        for cap in report.capacity:
            st.markdown(f"{_badge(cap.register)} **{cap.area}** — {cap.workload_level}")
            if cap.recommendation:
                st.caption(cap.recommendation)

    with tabs[7]:
        st.caption(narrative.forecast_note)
        cols = st.columns(len(report.forecast))
        for col, f in zip(cols, report.forecast):
            with col:
                st.markdown(f"### {f.name}")
                st.caption(f.growth_label + f" · confidence {f.confidence:.0f}%")
                for area, val in f.demand.items():
                    st.caption(f"{area}: {val}")
        st.markdown("**Assumptions**")
        _bullets(report.forecast[0].assumptions if report.forecast else [], "")

    with tabs[8]:
        for b in report.benchmarks:
            st.markdown(f"**{b.dimension}**")
            if b.note:
                st.caption(b.note)
            for c in b.comparisons:
                st.caption(f"• {c['group']}: {c['hiring_health']} · avg capability {c.get('avg_capability')} · {c.get('positive_share')}% positive ({c['count']})")

    with tabs[9]:
        st.caption(narrative.optimization_note)
        for o in report.optimizations:
            st.markdown(f"**[{o.priority}] {o.area}** — impact {o.impact} · effort {o.effort}")
            st.caption(o.recommendation)

    with tabs[10]:
        _render_dashboard(report)


def _render_dashboard(report: HiringIntelligenceReport) -> None:
    """Render the enterprise workforce dashboard (Module 11)."""
    charts = report.charts
    health = charts.get("hiring_health", {})
    st.markdown("**Hiring health**")
    if isinstance(health.get("value"), (int, float)):
        st.progress(max(0.0, min(1.0, health["value"] / 100.0)))
    st.caption(f"{health.get('label', 'n/a')}")

    st.markdown("**Executive KPIs**")
    for name, k in charts.get("executive_kpis", {}).items():
        val = f"{k['value']:.0f}" if isinstance(k.get("value"), (int, float)) else "n/a"
        st.caption(f"{_badge(k.get('register'))} {name}: {k.get('label')} ({val})")

    st.markdown("**Pipeline flow**")
    for step in charts.get("pipeline_flow", []):
        st.caption(f"{_badge(step.get('register'))} {step.get('stage')} — {step.get('severity')}")

    st.markdown("**Department / role comparison**")
    for row in charts.get("department_comparison", [])[:8]:
        st.caption(f"{row['dimension']}: {row['group']} — {row['hiring_health']} ({row['count']})")

    st.markdown("**Optimization opportunities**")
    for o in charts.get("optimization_opportunities", []):
        st.caption(f"[{o['priority']}] {o['area']} — impact {o['impact']} / effort {o['effort']}")


def _bar(data: dict) -> None:
    """Render a simple horizontal bar view for a ``{label: count}`` mapping."""
    if not data:
        st.caption("No data.")
        return
    peak = max([v for v in data.values() if isinstance(v, (int, float))] or [1]) or 1
    for label, value in data.items():
        if isinstance(value, (int, float)):
            st.caption(f"{label}: {'▇' * int(round(value / peak * 12)) or '·'} {value}")


def _bullets(items: List[str], empty_message: str) -> None:
    """Render a bullet list, or a caption when empty."""
    if not items:
        if empty_message:
            st.caption(empty_message)
        return
    for item in items:
        st.write("•", item)


# ---------------------------------------------------------------------------
# Standalone workspace
# ---------------------------------------------------------------------------

RepositoryFactory = Callable[[], Any]


def render_hiring_intelligence_workspace(repository_factory: RepositoryFactory, *, insights_fn=None) -> None:
    """Render the Hiring Intelligence workspace (organization-level; analyze a cohort)."""
    st.title("📈 Enterprise Hiring Intelligence & Workforce Analytics")
    st.caption(
        "TalentMind's enterprise workforce intelligence layer. It helps CHROs, "
        "CEOs, Talent Acquisition leaders, HR Operations, Finance and executives "
        "understand the health of the entire hiring organization with transparent, "
        "evidence-backed analytics, strategic insights and optimization "
        "recommendations — never fabricating enterprise metrics or historical data."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Analytics data is not ready: {exc}")
        return

    cohort_size = st.slider("Analyzed cohort size", min_value=3, max_value=ANALYTICS_COHORT, value=min(12, ANALYTICS_COHORT), key="hi_cohort")
    jd_text = st.text_area("Optional job description (sharpens role alignment across the cohort)", key="hi_jd")

    if st.button("📈 Generate workforce intelligence", type="primary", key="hi_run"):
        candidates = repository.sample(limit=cohort_size)
        if not candidates:
            st.info("No candidates available.")
            return
        render_hiring_intelligence(candidates, jd=jd_text, insights_fn=insights_fn, limit=cohort_size, key_prefix="hi_ws")
