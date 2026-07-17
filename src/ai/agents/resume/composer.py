"""Deterministic composer for the ResumeAnalystAgent (Module 16 / Safety).

Maps the evidence dict → a :class:`ResumeAnalysis`-shaped dict, purely by
restating and organizing the deterministic reports. Registered for the offline
``local`` provider so the agent works with zero external dependencies and cannot
hallucinate: the analysis is a pure function of the resume evidence.

The same evidence is embedded in the prompt for real providers, so the two paths
reason over identical facts.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.resume import report
from src.ai.agents.resume.report import band


def _executive_summary(ev: dict[str, Any], quality: dict[str, float]) -> str:
    """Compose the executive summary from the evidence + dimensions."""
    doc = ev.get("document", {})
    overall = quality.get("overall", 0.0)
    yoe = doc.get("years_of_experience", 0.0)
    headline = doc.get("headline") or (
        doc.get("experiences", [{}])[0].get("title", "candidate")
        if doc.get("experiences")
        else "candidate"
    )
    sections = len(doc.get("sections_present", []))
    return (
        f"Resume for {headline} (~{yoe:.0f} yrs experience) reads as "
        f"{band(overall).lower()} overall resume quality ({overall:.0f}/100). "
        f"{sections}/10 canonical sections present. This is a resume-quality "
        f"assessment — it does not rank or score the candidate for hiring."
    )


def _strengths(ev: dict[str, Any], quality: dict[str, float]) -> list[str]:
    """Derive strengths from the highest-scoring dimensions + concrete signals."""
    metrics = ev.get("metrics", {})
    strengths: list[str] = []
    top = sorted(
        ((k, v) for k, v in quality.items() if k != "overall"),
        key=lambda kv: kv[1],
        reverse=True,
    )
    for name, value in top[:3]:
        if value >= 60:
            strengths.append(
                f"{name.replace('_', ' ').title()} is {band(value).lower()} ({value:.0f}/100)."
            )
    if metrics.get("quantified_statements"):
        strengths.append(f"{len(metrics['quantified_statements'])} quantified achievement(s).")
    if metrics.get("modern_tech"):
        strengths.append(
            "Modern technology footprint: " + ", ".join(metrics["modern_tech"][:5]) + "."
        )
    return strengths or ["Baseline resume structure is in place."]


def _weaknesses(ev: dict[str, Any], quality: dict[str, float]) -> list[str]:
    """Derive weaknesses from the lowest-scoring dimensions + gaps."""
    weaknesses: list[str] = []
    low = sorted(((k, v) for k, v in quality.items() if k != "overall"), key=lambda kv: kv[1])
    for name, value in low[:3]:
        if value < 55:
            weaknesses.append(
                f"{name.replace('_', ' ').title()} is {band(value).lower()} ({value:.0f}/100)."
            )
    metrics = ev.get("metrics", {})
    if not metrics.get("quantified_statements"):
        weaknesses.append("Achievements are not quantified.")
    return weaknesses or ["No major weaknesses detected in the resume structure."]


def _confidence_note(ev: dict[str, Any]) -> str:
    """State confidence + uncertainty based on how much evidence exists."""
    doc = ev.get("document", {})
    bullets = ev.get("metrics", {}).get("bullet_count", 0)
    if bullets < 4 or len(doc.get("sections_present", [])) < 4:
        return (
            "Confidence is limited — the resume provides thin evidence (few bullets "
            "or sections), so several observations are inference and should be "
            "verified with the candidate."
        )
    return (
        "Confidence is solid — observations are grounded in multiple resume "
        "sections. Suggestions are advisory and separate from the extracted evidence."
    )


def _evidence_list(ev: dict[str, Any]) -> list[str]:
    """Return a compact list of the concrete evidence the analysis relied on."""
    doc = ev.get("document", {})
    metrics = ev.get("metrics", {})
    items = [
        f"{len(doc.get('experiences', []))} experience entr(ies), {metrics.get('bullet_count', 0)} bullet(s).",
        f"{doc.get('skill_count', len(doc.get('skills', [])))} skill(s); "
        f"{len(metrics.get('modern_tech', []))} modern, {len(metrics.get('dated_tech', []))} dated.",
        f"Sections present: {', '.join(doc.get('sections_present', [])) or 'none'}.",
    ]
    if metrics.get("quantified_statements"):
        items.append("Quantified: " + metrics["quantified_statements"][0][:120])
    return items


def compose_resume_analysis(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose a :class:`ResumeAnalysis` dict from evidence."""
    ev = evidence or {}
    metrics = ev.get("metrics", {})
    quality = metrics.get("dimensions", {}) or {}

    risk_findings = ev.get("risks", [])
    risk_report = {
        "level": ev.get("risk_level", "Low"),
        "findings": risk_findings,
        "positive_signals": ev.get("positive_signals", []),
    }

    return {
        "executive_summary": _executive_summary(ev, quality),
        "strengths": _strengths(ev, quality),
        "weaknesses": _weaknesses(ev, quality),
        "career_story": report.build_career_story(ev),
        "resume_quality": {k: round(v, 1) for k, v in quality.items()},
        "structure": report.build_structure(ev),
        "writing": report.build_writing(ev),
        "technical": report.build_technical(ev),
        "projects": report.build_projects(ev),
        "achievements": report.build_achievements(ev),
        "ats_report": report.build_ats(ev),
        "risk_report": risk_report,
        "improvement_plan": report.generate_improvements(ev),
        "confidence_note": _confidence_note(ev),
        "evidence": _evidence_list(ev),
    }
