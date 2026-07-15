"""Professional visualizations (Module 10).

Two layers, cleanly separated:

* **Chart data** — pure, JSON-serializable builders (:func:`build_chart_data`)
  that turn the existing engine outputs into the numbers a chart needs. These are
  stored on the report (so exports can embed them) and are trivially testable.
* **Streamlit renderers** — thin functions that draw the data with native
  Streamlit primitives (``st.bar_chart``, ``st.progress``, ``st.metric``). No
  matplotlib (never a project dependency). The radar uses Plotly *if available*
  and degrades to a bar chart otherwise, so the dashboard never hard-fails.

Enterprise styling is provided by the branding module; here we only shape data.
"""

from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Pure chart-data builders
# ---------------------------------------------------------------------------


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce ``value`` to a float, defaulting on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_chart_data(
    *,
    intelligence: Dict[str, Any],
    timeline: Dict[str, Any],
    risk: Dict[str, Any],
    committee: Dict[str, Any],
    interview: Dict[str, Any],
    resume: Dict[str, Any],
) -> Dict[str, Any]:
    """Return every chart's data (pure; safe to serialize into the report)."""
    intelligence = intelligence or {}
    timeline = timeline or {}
    risk = risk or {}
    committee = committee or {}
    interview = interview or {}
    resume = resume or {}

    # Hiring Scorecard — headline dimensions.
    scorecard = {
        "Overall": _num(intelligence.get("overall_score")),
        "Technical": _num(intelligence.get("technical_score")),
        "Leadership": _num(intelligence.get("leadership_score")),
        "Career Growth": _num(intelligence.get("career_growth_score")),
        "Learning Velocity": _num(intelligence.get("learning_velocity")),
    }

    # Radar — capability profile (same axes as the scorecard, radar-shaped).
    radar = dict(scorecard)

    # Risk Matrix — sub-risk levels mapped to 0-100 severity.
    level_map = {"low": 20.0, "medium": 55.0, "high": 90.0, "unknown": 0.0}

    def _sev(level: Any) -> float:
        return level_map.get(str(level or "").strip().lower(), 0.0)

    risk_matrix = {
        "Employment Gap": _sev(risk.get("employment_gap_risk")),
        "Job Hopping": _sev(risk.get("job_hopping_risk")),
        "Skill Stagnation": _sev(risk.get("skill_stagnation_risk")),
        "Technical Depth": _sev(risk.get("technical_depth_risk")),
        "Leadership": _sev(risk.get("leadership_risk")),
        "Communication": _sev(risk.get("communication_risk")),
    }

    # Consensus meter — map weighted stance (-2..3) onto 0..1 (matches committee UI).
    stance = _num((committee.get("consensus") or {}).get("weighted_stance"))
    consensus_meter = max(0.0, min(1.0, (stance + 2.0) / 5.0))

    # Confidence distribution — the five explained committee signals.
    conf = committee.get("confidence") or {}
    confidence_distribution = {
        "Evidence Coverage": _num(conf.get("evidence_coverage")),
        "Consensus Strength": _num(conf.get("consensus_strength")),
        "Confidence Distribution": _num(conf.get("confidence_distribution")),
        "Decision Stability": _num(conf.get("decision_stability")),
        "Unknown Risk": _num(conf.get("unknown_risk")),
    }

    # Career growth — trajectory signals over the timeline.
    career_growth = {
        "Timeline": _num(timeline.get("timeline_score")),
        "Growth": _num(timeline.get("career_growth_score")),
        "Stability": _num(timeline.get("career_stability")),
        "Domain Consistency": _num(timeline.get("domain_consistency")),
    }

    # Skill distribution — resume-quality dimensions (labelled as quality, not hire).
    quality = resume.get("quality") or {}
    skill_distribution = {
        k.replace("_", " ").title(): _num(v)
        for k, v in quality.items()
        if isinstance(v, (int, float))
    }

    # Interview roadmap — count of items per round.
    interview_roadmap = {
        "Technical": len(interview.get("technical_topics", []) or []),
        "System Design": len(interview.get("system_design_topics", []) or []),
        "Behavioral": len(interview.get("behavioral_questions", []) or []),
        "Leadership": len(interview.get("leadership_questions", []) or []),
        "Coding": len(interview.get("coding_focus", []) or []),
    }

    return {
        "scorecard": scorecard,
        "radar": radar,
        "risk_matrix": risk_matrix,
        "consensus_meter": consensus_meter,
        "confidence_distribution": confidence_distribution,
        "career_growth": career_growth,
        "skill_distribution": skill_distribution,
        "interview_roadmap": interview_roadmap,
    }


# ---------------------------------------------------------------------------
# Streamlit renderers (thin; native primitives, no matplotlib)
# ---------------------------------------------------------------------------


def _bar(st, data: Dict[str, float], caption: str = "") -> None:
    """Render a labelled bar chart from ``{label: value}``."""
    if not data:
        st.caption("No data available.")
        return
    st.bar_chart(data)
    if caption:
        st.caption(caption)


def render_scorecard(st, charts: Dict[str, Any]) -> None:
    """Render the hiring scorecard as metrics + a bar chart."""
    data = charts.get("scorecard", {})
    cols = st.columns(len(data) or 1)
    for col, (label, value) in zip(cols, data.items()):
        col.metric(label, f"{value:.0f}/100")
    _bar(st, data, "Hiring Scorecard — Candidate Intelligence dimensions (not a hiring decision).")


def render_radar(st, charts: Dict[str, Any]) -> None:
    """Render the capability radar (Plotly if available, else a bar chart)."""
    data = charts.get("radar", {})
    if not data:
        st.caption("No capability data.")
        return
    try:  # Plotly is optional; degrade gracefully.
        import plotly.graph_objects as go  # type: ignore

        labels = list(data.keys())
        values = list(data.values())
        fig = go.Figure(
            data=[
                go.Scatterpolar(
                    r=values + values[:1],
                    theta=labels + labels[:1],
                    fill="toself",
                    name="Capability",
                )
            ]
        )
        fig.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 100]}},
            showlegend=False,
            margin=dict(l=30, r=30, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        _bar(st, data, "Capability profile.")


def render_risk_matrix(st, charts: Dict[str, Any]) -> None:
    """Render the risk matrix as a severity bar chart."""
    _bar(st, charts.get("risk_matrix", {}), "Risk Matrix — sub-risk severity (higher is riskier).")


def render_consensus_meter(st, charts: Dict[str, Any]) -> None:
    """Render the committee consensus meter."""
    meter = float(charts.get("consensus_meter", 0.0))
    st.caption("Committee Consensus Meter (No Hire ◄──► Strong Hire)")
    st.progress(max(0.0, min(1.0, meter)))


def render_confidence_distribution(st, charts: Dict[str, Any]) -> None:
    """Render the five explained confidence signals as progress bars."""
    data = charts.get("confidence_distribution", {})
    if not data:
        st.caption("No confidence signals (committee not convened).")
        return
    for label, value in data.items():
        st.caption(f"{label} — {value:.0f}/100")
        st.progress(max(0.0, min(1.0, value / 100.0)))


def render_career_growth(st, charts: Dict[str, Any]) -> None:
    """Render the career-growth trajectory chart."""
    _bar(st, charts.get("career_growth", {}), "Career Growth — trajectory signals (Career Timeline Intelligence).")


def render_skill_distribution(st, charts: Dict[str, Any]) -> None:
    """Render the resume-quality distribution chart."""
    _bar(st, charts.get("skill_distribution", {}), "Resume-quality distribution (resume quality only, not a hiring score).")


def render_interview_roadmap(st, charts: Dict[str, Any]) -> None:
    """Render the interview roadmap (topics per round)."""
    _bar(st, charts.get("interview_roadmap", {}), "Interview Roadmap — topics per round.")


def render_all(st, charts: Dict[str, Any]) -> None:
    """Render the full visualization suite in a professional layout."""
    render_scorecard(st, charts)
    left, right = st.columns(2)
    with left:
        render_radar(st, charts)
        render_risk_matrix(st, charts)
        render_career_growth(st, charts)
    with right:
        render_consensus_meter(st, charts)
        render_confidence_distribution(st, charts)
        render_skill_distribution(st, charts)
    render_interview_roadmap(st, charts)
