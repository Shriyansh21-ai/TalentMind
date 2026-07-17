"""Deterministic composer for the WorkforceNarrative (offline reasoning).

Maps the aggregated analytics evidence to a :class:`WorkforceNarrative`-shaped
dict by **restating and organizing** the computed cohort analytics — never
fabricating a trend, KPI, forecast or enterprise statistic (Module 15). This lets
the workforce-intelligence agent run fully offline with a structural
no-fabrication guarantee.
"""

from __future__ import annotations

from typing import Any


def compose_workforce_narrative(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose a :class:`WorkforceNarrative` from evidence."""
    analytics = evidence.get("analytics") or evidence
    cohort_size = analytics.get("cohort_size", 0)
    data_available = bool(analytics.get("data_available"))
    kpis = analytics.get("kpis", [])
    bottlenecks = analytics.get("bottlenecks", [])
    trends = analytics.get("trends", [])
    optimizations = analytics.get("optimizations", [])
    key_insights = analytics.get("key_insights", [])
    forecast = analytics.get("forecast", [])

    health = next((k for k in kpis if k.get("name") == "Hiring Health Index"), {})
    health_label = health.get("label", "n/a")

    summary = (
        f"Workforce hiring intelligence across an analyzed cohort of {cohort_size} candidate(s). "
        f"Hiring Health Index: {health_label}"
        + (
            f" ({health.get('value'):.0f}/100)."
            if isinstance(health.get("value"), (int, float))
            else "."
        )
        + " This is strategic organizational intelligence — not candidate ranking — and it reports "
        "unavailable metrics honestly rather than fabricating them."
    )

    estimated_bottlenecks = [b for b in bottlenecks if b.get("register") == "Estimated"]
    pipeline_note = (
        "Estimated bottleneck(s): " + "; ".join(b["stage"] for b in estimated_bottlenecks) + "."
        if estimated_bottlenecks
        else "No cohort-derivable bottlenecks; delay-based bottlenecks need connected timing data."
    )

    unavailable_trends = [t for t in trends if t.get("register") == "Unavailable"]
    trend_note = (
        f"{len(unavailable_trends)} of {len(trends)} trends are UNAVAILABLE — time-series analytics require a "
        "connected data source."
        if unavailable_trends
        else "Trends computed from the connected analytics source."
    )

    observed_kpis = [k for k in kpis if k.get("register") == "Observed"]
    kpi_note = (
        f"{len(observed_kpis)} of {len(kpis)} KPIs are evidence-backed from the cohort; the rest need "
        "connected governance/analytics data."
    )

    forecast_note = (
        "Scenario forecasts scale the analyzed-cohort baseline (Conservative/Growth/Aggressive) — directional, "
        "not predictions, with explicit assumptions."
        if forecast
        else "No forecast produced."
    )

    top_opts = [o for o in optimizations if o.get("priority") in ("Critical", "High")]
    optimization_note = (
        "Priority optimizations: " + "; ".join(o["recommendation"] for o in top_opts[:3]) + "."
        if top_opts
        else "No high-priority optimizations surfaced."
    )

    data_note = (
        "A workforce-analytics source is connected; time-series, team and capacity analytics are enabled."
        if data_available
        else "No workforce-analytics source connected — trends, delays, team breakdowns and capacity are "
        "UNAVAILABLE and marked as such (Module 15)."
    )

    strategic: list[str] = [o["recommendation"] for o in top_opts[:4]]
    if not data_available:
        strategic.append(
            "Connect an HR data warehouse / people-analytics source to unlock full workforce intelligence."
        )

    assumptions = [
        "Analytics run over a bounded analyzed cohort, not the full organization.",
        "Cohort metrics restate existing per-candidate intelligence; no enterprise statistics are invented.",
    ]

    confidence_note = (
        "Confidence is solid on the cohort-derived KPIs; org-wide trends/capacity remain unavailable without a data source."
        if not data_available
        else "Confidence is solid — cohort intelligence plus connected analytics data."
    )

    return {
        "executive_summary": summary,
        "health_note": f"Hiring Health Index is {health_label} over {cohort_size} candidate(s).",
        "pipeline_note": pipeline_note,
        "trend_note": trend_note,
        "kpi_note": kpi_note,
        "capacity_note": (
            "Capacity workloads are UNAVAILABLE without requisition/headcount data."
            if not data_available
            else "Capacity computed from the connected source."
        ),
        "forecast_note": forecast_note,
        "optimization_note": optimization_note,
        "data_availability_note": data_note,
        "key_insights": key_insights or ["Insufficient cohort data to surface insights."],
        "assumptions": assumptions,
        "strategic_recommendations": list(dict.fromkeys(strategic))
        or ["Maintain current hiring practices; no material gaps surfaced."],
        "confidence_note": confidence_note,
    }
