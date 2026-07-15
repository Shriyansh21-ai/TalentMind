"""Deterministic composer for the InterviewStudioNarrative (offline reasoning).

Maps the aggregated evidence dict to an :class:`InterviewStudioNarrative`-shaped
dict by **restating and organizing** the existing intelligence — never inventing
a candidate fact, an interview result or a recommendation (Module 16). This is
what lets the Interview Studio run fully offline with zero external dependencies
and a structural no-hallucination guarantee: the narrative is a pure function of
the deterministic engines' output.

The same evidence is embedded in the prompt for real providers, so online and
offline modes agree on the facts.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _overview_line(evidence: Dict[str, Any]) -> str:
    """Return a one-line candidate descriptor for the summary opener."""
    ov = evidence.get("candidate_overview") or {}
    title = ov.get("title") or "the candidate"
    company = ov.get("company") or ""
    years = ov.get("years_of_experience")
    parts = [title]
    if company:
        parts.append(f"at {company}")
    if isinstance(years, (int, float)) and years:
        parts.append(f"with {years:.0f} years of experience")
    return " ".join(parts)


def _recommendation(evidence: Dict[str, Any]) -> tuple:
    """Return ``(label, source)`` for the authoritative upstream recommendation."""
    committee = evidence.get("committee") or {}
    consensus = committee.get("consensus") or {}
    if consensus.get("recommendation"):
        return consensus["recommendation"], "AI Hiring Committee"
    recommendation = evidence.get("recommendation") or {}
    if recommendation.get("recommendation"):
        return recommendation["recommendation"], "Hiring Recommendation engine"
    return "", ""


def _readiness(evidence: Dict[str, Any]) -> str:
    """Return a qualitative interview-readiness label (never a score)."""
    plan = evidence.get("interview") or {}
    has_plan = bool(plan.get("technical_topics") or plan.get("behavioral_questions"))
    risk = evidence.get("risk") or {}
    high_risk = str(risk.get("risk_level", "")).lower() == "high"
    if not has_plan:
        return "Needs Preparation"
    if high_risk:
        return "Ready — Validate Risks"
    return "Ready to Interview"


def _key_probes(evidence: Dict[str, Any]) -> List[str]:
    """Collect the highest-priority things the interview must probe."""
    probes: List[str] = []
    committee = evidence.get("committee") or {}
    probes.extend((committee.get("decision") or {}).get("interview_priorities", []) or [])
    recommendation = evidence.get("recommendation") or {}
    probes.extend(recommendation.get("interview_focus", []) or [])
    intelligence = evidence.get("intelligence") or {}
    probes.extend(f"Verify strength: {s}" for s in (intelligence.get("strengths") or [])[:2])
    return list(dict.fromkeys(p for p in probes if p))[:5]


def _watch_areas(evidence: Dict[str, Any]) -> List[str]:
    """Collect the concerns / risks the panel should watch for."""
    watch: List[str] = []
    risk = evidence.get("risk") or {}
    watch.extend(risk.get("red_flags") or [])
    intelligence = evidence.get("intelligence") or {}
    watch.extend(intelligence.get("weaknesses") or [])
    recommendation = evidence.get("recommendation") or {}
    watch.extend(recommendation.get("concerns") or [])
    return list(dict.fromkeys(w for w in watch if w))[:5]


def _confidence_note(evidence: Dict[str, Any]) -> str:
    """Return a qualitative confidence note based on evidence coverage."""
    committee = evidence.get("committee") or {}
    overall = (committee.get("confidence") or {}).get("overall")
    if overall is None:
        overall = (evidence.get("intelligence") or {}).get("confidence")
    if not isinstance(overall, (int, float)):
        return (
            "Confidence in this interview plan is moderate; evidence sources are "
            "partial. The plan validates the engines' signals rather than replacing them."
        )
    if overall >= 75:
        label = "high"
        tail = "The plan can be run as-is."
    elif overall >= 55:
        label = "moderate"
        tail = "Weight the risk-validation stage."
    else:
        label = "low"
        tail = "Evidence is thin — treat every claim as unverified until the interview."
    return (
        f"Confidence in this plan is {label} (evidence coverage {overall:.0f}/100); "
        f"this reflects the engines' coverage, not a hiring score. {tail}"
    )


def compose_interview_narrative(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically compose an :class:`InterviewStudioNarrative` from evidence."""
    overview = _overview_line(evidence)
    role = evidence.get("role_name") or evidence.get("role") or "the role"
    depth = evidence.get("depth") or "standard"
    rec_label, rec_source = _recommendation(evidence)

    rec_clause = (
        f" The upstream recommendation is '{rec_label}' (per the {rec_source}); "
        "the interview is designed to validate it, not re-open the ranking."
        if rec_label
        else " No upstream hiring recommendation was available, so the interview is the primary signal."
    )
    summary = (
        f"This is a personalized {depth} interview plan for {overview}, targeting a "
        f"{role} loop.{rec_clause} Every question, rubric and risk-validation traces "
        "back to TalentMind's existing intelligence — nothing here is invented."
    )

    probes = _key_probes(evidence)
    watch = _watch_areas(evidence)

    strategy_overview = (
        f"The loop is calibrated to the candidate's seniority and role fit. Depth "
        f"and difficulty scale to the evidence; priorities follow the committee and "
        f"the recommendation engine."
    )
    personalization = (
        "Personalized to this candidate: the technical stage probes their proven "
        "skills, the behavioral stage targets the development areas the intelligence "
        "engine surfaced, and the risk stage validates the specific flags on record."
        if (probes or watch)
        else "Personalization is limited by thin evidence; the plan falls back to a "
        "role-appropriate default loop."
    )
    coverage = (
        f"Coverage spans technical depth, {'system design, ' if depth != 'screen' else ''}"
        "coding, behavioral and (where warranted) leadership, plus a debrief mapped to the decision matrix."
    )
    risk_note = (
        "Each flagged risk is converted into a validation question with expected "
        "evidence and a pass criterion; watch areas: " + "; ".join(watch) + "."
        if watch
        else "No material risks were flagged; the risk stage confirms baseline claims only."
    )

    return {
        "interview_summary": summary,
        "strategy_overview": strategy_overview,
        "recommended_focus": ("; ".join(probes) if probes else "Confirm role fit and technical depth."),
        "personalization_note": personalization,
        "coverage_note": coverage,
        "risk_validation_note": risk_note,
        "readiness_label": _readiness(evidence),
        "key_probes": probes,
        "watch_areas": watch,
        "confidence_note": _confidence_note(evidence),
    }
