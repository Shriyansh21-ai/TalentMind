"""Deterministic composer for the JDAnalystAgent (Module 16 / Safety).

Maps the evidence dict → a :class:`JDAnalysis`-shaped dict, purely by restating
and organizing the deterministic reports. Registered for the offline ``local``
provider so the agent works with zero external dependencies and cannot
hallucinate: the analysis is a pure function of the JD evidence. The same
evidence is embedded in the prompt for real providers.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.jd import report
from src.ai.agents.jd.report import band


def _executive_summary(ev: Dict[str, Any], quality: Dict[str, float], role: Dict[str, Any]) -> str:
    """Compose the executive summary from evidence + dimensions + role."""
    doc = ev.get("document", {})
    overall = quality.get("overall", 0.0)
    title = doc.get("title") or "this role"
    sections = len(doc.get("sections_present", []))
    return (
        f"Job description for '{title}' reads as {band(overall).lower()} overall JD "
        f"quality ({overall:.0f}/100); {sections}/13 canonical sections present. "
        f"Inferred as a {role.get('seniority', 'unspecified').lower()} role. This is a "
        f"job-description quality + intent assessment — it does not rank candidates."
    )


def _strengths(ev: Dict[str, Any], quality: Dict[str, float]) -> List[str]:
    """Derive strengths from the highest-scoring dimensions + concrete signals."""
    doc = ev.get("document", {})
    strengths: List[str] = []
    top = sorted(((k, v) for k, v in quality.items() if k != "overall"), key=lambda kv: kv[1], reverse=True)
    for name, value in top[:3]:
        if value >= 60:
            strengths.append(f"{name.replace('_', ' ').title()} is {band(value).lower()} ({value:.0f}/100).")
    if doc.get("compensation"):
        strengths.append("Compensation is disclosed.")
    if doc.get("preferred"):
        strengths.append("Requirements are split into mandatory vs preferred.")
    return strengths or ["Baseline JD structure is present."]


def _weaknesses(ev: Dict[str, Any], quality: Dict[str, float]) -> List[str]:
    """Derive weaknesses from the lowest-scoring dimensions + gaps."""
    weaknesses: List[str] = []
    low = sorted(((k, v) for k, v in quality.items() if k != "overall"), key=lambda kv: kv[1])
    for name, value in low[:3]:
        if value < 55:
            weaknesses.append(f"{name.replace('_', ' ').title()} is {band(value).lower()} ({value:.0f}/100).")
    doc = ev.get("document", {})
    if not doc.get("compensation"):
        weaknesses.append("No compensation disclosed.")
    return weaknesses or ["No major weaknesses detected in the JD structure."]


def _confidence_note(ev: Dict[str, Any]) -> str:
    """State confidence + uncertainty based on how much evidence exists."""
    doc = ev.get("document", {})
    present = len(doc.get("sections_present", []))
    if present < 5 or not doc.get("requirements"):
        return (
            "Confidence is limited — the JD provides thin evidence (few sections or "
            "no explicit requirements), so several inferences are low-confidence and "
            "should be validated with the hiring manager."
        )
    return (
        "Confidence is solid — inferences are grounded in multiple JD sections. Each "
        "inference carries its own confidence; suggestions are advisory and separate "
        "from the extracted evidence."
    )


def _evidence_list(ev: Dict[str, Any]) -> List[str]:
    """Return a compact list of the concrete evidence the analysis relied on."""
    doc = ev.get("document", {})
    m = ev.get("metrics", {})
    items = [
        f"{len(doc.get('requirements', []))} requirement line(s), "
        f"{len(doc.get('responsibilities', []))} responsibility line(s).",
        f"{m.get('tech_count', 0)} technologies across "
        f"{sum(bool(m.get(k)) for k in ('languages','frameworks','cloud','ai_ml','devops','data'))} categories.",
        f"Sections present: {', '.join(doc.get('sections_present', [])) or 'none'}.",
    ]
    if doc.get("compensation"):
        items.append("Compensation present: " + str(doc["compensation"])[:80])
    return items


def compose_jd_analysis(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically compose a :class:`JDAnalysis` dict from evidence."""
    ev = evidence or {}
    m = ev.get("metrics", {})
    quality = m.get("dimensions", {}) or {}

    role = report.build_role(ev)
    risk_report = {
        "level": ev.get("risk_level", "Low"),
        "findings": ev.get("risks", []),
        "positive_signals": ev.get("positive_signals", []),
    }
    market = {
        "summary": _market_summary(ev),
        "estimates": ev.get("market_estimates", []),
    }

    return {
        "executive_summary": _executive_summary(ev, quality, role),
        "strengths": _strengths(ev, quality),
        "weaknesses": _weaknesses(ev, quality),
        "role_intelligence": role,
        "technical_intelligence": report.build_technical(ev),
        "hiring_intent": report.build_hiring_intent(ev),
        "organization_intelligence": report.build_organization(ev),
        "requirement_hierarchy": report.build_requirement_hierarchy(ev),
        "market_intelligence": market,
        "quality": {k: round(v, 1) for k, v in quality.items()},
        "structure": report.build_structure(ev),
        "risk_report": risk_report,
        "improvement_plan": report.generate_improvements(ev),
        "confidence_note": _confidence_note(ev),
        "evidence": _evidence_list(ev),
    }


def _market_summary(ev: Dict[str, Any]) -> str:
    """One-line summary of the market posture from the estimates."""
    estimates = ev.get("market_estimates", [])
    by_dim = {e["dimension"]: e["assessment"] for e in estimates}
    demand = by_dim.get("skill_demand", "n/a")
    difficulty = by_dim.get("hiring_difficulty", "n/a")
    return (
        f"Heuristic market read (offline): skill demand — {demand}; hiring difficulty "
        f"— {difficulty}. Estimates are directional, each with its own confidence."
    )
