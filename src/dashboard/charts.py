"""Plotly figure builders for the Recruiter Dashboard (Module 5).

Each function consumes an aggregation from ``src/dashboard/analytics.py`` and
returns a styled ``plotly.graph_objects.Figure``. Styling is centralized so every
chart shares one professional, theme-aware look. No Streamlit and no data
aggregation live here — figures in, figures out.
"""

from __future__ import annotations

import plotly.graph_objects as go

CountPairs = list[tuple[str, int]]

# ---------------------------------------------------------------------------
# Shared visual system
# ---------------------------------------------------------------------------

# A single categorical sequence keeps every chart visually consistent.
_PRIMARY = "#2563eb"  # blue-600
_SEQUENCE = [
    "#2563eb",
    "#0891b2",
    "#7c3aed",
    "#db2777",
    "#ea580c",
    "#16a34a",
    "#ca8a04",
    "#4f46e5",
]
_RISK_COLORS = {"Low": "#16a34a", "Medium": "#ca8a04", "High": "#dc2626"}
_RECOMMENDATION_COLORS = {
    "Strong Hire": "#16a34a",
    "Hire": "#2563eb",
    "Hold": "#ca8a04",
    "Reject": "#dc2626",
}

_MARGIN = dict(l=60, r=30, t=60, b=60)


def _style(fig: go.Figure, title: str, height: int = 360) -> go.Figure:
    """Apply the shared layout to a figure and return it."""
    fig.update_layout(
        title=dict(text=title, x=0.0, font=dict(size=16)),
        template="plotly_white",
        height=height,
        margin=_MARGIN,
        showlegend=fig.layout.showlegend,
        bargap=0.25,
    )
    return fig


def _empty(title: str, message: str = "No data available") -> go.Figure:
    """Return a styled placeholder figure for empty inputs."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#6b7280"),
    )
    fig.update_layout(
        title=dict(text=title, x=0.0, font=dict(size=16)),
        template="plotly_white",
        height=280,
        margin=_MARGIN,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# ---------------------------------------------------------------------------
# Pipeline charts
# ---------------------------------------------------------------------------


def hiring_funnel(pairs: CountPairs) -> go.Figure:
    """Build a hiring-funnel chart from cumulative ``(stage, count)`` pairs."""
    if not pairs or all(count == 0 for _, count in pairs):
        return _empty("Hiring Funnel", "No candidates in the pipeline yet")
    stages = [label for label, _ in pairs]
    values = [count for _, count in pairs]
    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker=dict(color=_PRIMARY),
        )
    )
    fig.update_layout(showlegend=False)
    return _style(fig, "Hiring Funnel", height=420)


def stage_distribution_chart(counts: dict[str, int]) -> go.Figure:
    """Build a bar chart of candidates per pipeline stage (snapshot)."""
    if not counts or all(v == 0 for v in counts.values()):
        return _empty("Stage Distribution", "No candidates in the pipeline yet")
    labels = list(counts.keys())
    values = list(counts.values())
    fig = go.Figure(
        go.Bar(x=labels, y=values, marker_color=_PRIMARY, text=values, textposition="auto")
    )
    fig.update_layout(showlegend=False, xaxis_tickangle=-35)
    return _style(fig, "Stage Distribution")


def pipeline_chart(counts: dict[str, int]) -> go.Figure:
    """Build a horizontal bar of active-pipeline occupancy per stage."""
    if not counts or all(v == 0 for v in counts.values()):
        return _empty("Hiring Pipeline", "No candidates in the pipeline yet")
    labels = list(counts.keys())
    values = list(counts.values())
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=_SEQUENCE[2],
            text=values,
            textposition="auto",
        )
    )
    fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
    return _style(fig, "Hiring Pipeline", height=420)


# ---------------------------------------------------------------------------
# Distribution charts
# ---------------------------------------------------------------------------


def risk_distribution_chart(counts: dict[str, int]) -> go.Figure:
    """Build a donut chart of Low/Medium/High risk composition."""
    labels = [k for k, v in counts.items() if v > 0]
    values = [counts[k] for k in labels]
    if not values:
        return _empty("Risk Distribution")
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=[_RISK_COLORS.get(k, _PRIMARY) for k in labels]),
            textinfo="label+percent",
        )
    )
    fig.update_layout(showlegend=True)
    return _style(fig, "Risk Distribution")


def score_distribution_chart(values: list[float]) -> go.Figure:
    """Build a histogram of candidate overall scores."""
    if not values:
        return _empty("Candidate Score Distribution")
    fig = go.Figure(go.Histogram(x=values, nbinsx=20, marker_color=_SEQUENCE[3]))
    fig.update_layout(showlegend=False, xaxis_title="Overall Score", yaxis_title="Candidates")
    return _style(fig, "Candidate Score Distribution")


def experience_distribution_chart(values: list[float]) -> go.Figure:
    """Build a histogram of years-of-experience."""
    if not values:
        return _empty("Experience Distribution")
    fig = go.Figure(go.Histogram(x=values, nbinsx=20, marker_color=_SEQUENCE[1]))
    fig.update_layout(showlegend=False, xaxis_title="Years of Experience", yaxis_title="Candidates")
    return _style(fig, "Experience Distribution")


def horizontal_count_bar(pairs: CountPairs, title: str, color: str = _SEQUENCE[5]) -> go.Figure:
    """Build a titled horizontal bar chart from ``(label, count)`` pairs.

    Shared by any ranked-category chart (top skills, talent-pool sizes, ...) so
    the styling stays consistent and the code is not duplicated per chart.
    """
    if not pairs:
        return _empty(title)
    labels = [label for label, _ in pairs][::-1]
    values = [count for _, count in pairs][::-1]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=color))
    fig.update_layout(showlegend=False)
    return _style(fig, title, height=max(360, 22 * len(pairs)))


def top_skills_chart(pairs: CountPairs) -> go.Figure:
    """Build a horizontal bar of the most common skills."""
    return horizontal_count_bar(pairs, "Top Skills", color=_SEQUENCE[5])


def location_distribution_chart(pairs: CountPairs) -> go.Figure:
    """Build a bar chart of the most common candidate locations."""
    if not pairs:
        return _empty("Location Distribution")
    labels = [label for label, _ in pairs]
    values = [count for _, count in pairs]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=_SEQUENCE[0]))
    fig.update_layout(showlegend=False, xaxis_tickangle=-35)
    return _style(fig, "Location Distribution")


def company_distribution_chart(pairs: CountPairs) -> go.Figure:
    """Build a bar chart of the most common current employers."""
    if not pairs:
        return _empty("Company Distribution")
    labels = [label for label, _ in pairs]
    values = [count for _, count in pairs]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=_SEQUENCE[6]))
    fig.update_layout(showlegend=False, xaxis_tickangle=-35)
    return _style(fig, "Company Distribution")


def recommendation_distribution_chart(counts: dict[str, int]) -> go.Figure:
    """Build a bar chart of hiring-recommendation composition."""
    if not counts or all(v == 0 for v in counts.values()):
        return _empty("Hiring Recommendation Distribution")
    # Present in a sensible severity order when labels are recognised.
    order = ["Strong Hire", "Hire", "Hold", "Reject"]
    labels = [k for k in order if k in counts] + [k for k in counts if k not in order]
    values = [counts[k] for k in labels]
    colors = [_RECOMMENDATION_COLORS.get(k, _PRIMARY) for k in labels]
    fig = go.Figure(
        go.Bar(x=labels, y=values, marker_color=colors, text=values, textposition="auto")
    )
    fig.update_layout(showlegend=False)
    return _style(fig, "Hiring Recommendation Distribution")
