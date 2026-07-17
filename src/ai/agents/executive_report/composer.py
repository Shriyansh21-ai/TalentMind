"""Deterministic composer for the ExecutiveNarrative (offline reasoning).

Maps the aggregated evidence dict to an :class:`ExecutiveNarrative`-shaped dict by
**restating and organizing** the existing intelligence — never inventing a
conclusion (Module 16). This is what lets the executive report run fully offline
with zero external dependencies and a structural no-hallucination guarantee: the
narrative is a pure function of the deterministic engines' output.

The same evidence is embedded in the prompt for real providers, so online and
offline modes agree on the facts.
"""

from __future__ import annotations

from typing import Any


# Ordered preference for where the headline recommendation comes from. The
# committee's consensus is authoritative when present; otherwise the hiring
# recommendation engine; otherwise the candidate-intelligence engine.
def _headline_recommendation(evidence: dict[str, Any]) -> tuple:
    """Return ``(recommendation_label, source_label)`` from the best source."""
    committee = evidence.get("committee") or {}
    consensus = committee.get("consensus") or {}
    if consensus.get("recommendation"):
        return consensus["recommendation"], "AI Hiring Committee"

    recommendation = evidence.get("recommendation") or {}
    if recommendation.get("recommendation"):
        return recommendation["recommendation"], "Hiring Recommendation engine"

    intelligence = evidence.get("intelligence") or {}
    if intelligence.get("recommendation"):
        return intelligence["recommendation"], "Candidate Intelligence engine"

    return "Further Assessment", "TalentMind synthesis"


def _overview_line(evidence: dict[str, Any]) -> str:
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


def _first_sentences(text: str, limit: int = 2) -> str:
    """Return the first ``limit`` sentences of ``text`` (whitespace-collapsed)."""
    clean = " ".join((text or "").split())
    if not clean:
        return ""
    pieces = clean.replace("! ", ". ").replace("? ", ". ").split(". ")
    return ". ".join(p for p in pieces[:limit] if p).strip().rstrip(".") + "."


def _business_impact(evidence: dict[str, Any]) -> str:
    """Restate the business case from committee + recommendation + intelligence."""
    committee = evidence.get("committee") or {}
    decision = committee.get("decision") or {}
    if decision.get("business_justification"):
        return f"{decision['business_justification']} (per the AI Hiring Committee)."

    recommendation = evidence.get("recommendation") or {}
    reasons = recommendation.get("reasons") or []
    if reasons:
        return "The hiring recommendation engine cites: " + "; ".join(reasons[:3]) + "."

    intelligence = evidence.get("intelligence") or {}
    strengths = intelligence.get("strengths") or []
    if strengths:
        return "Candidate Intelligence highlights: " + "; ".join(strengths[:3]) + "."
    return "Business impact could not be substantiated from the available evidence."


def _technical_impact(evidence: dict[str, Any]) -> str:
    """Restate the technical case from committee + resume + intelligence."""
    committee = evidence.get("committee") or {}
    decision = committee.get("decision") or {}
    if decision.get("technical_justification"):
        return f"{decision['technical_justification']} (per the AI Hiring Committee)."

    intelligence = evidence.get("intelligence") or {}
    tech = intelligence.get("technical_score")
    resume = evidence.get("resume") or {}
    depth = (resume.get("quality") or {}).get("technical_depth")
    bits: list[str] = []
    if isinstance(tech, (int, float)):
        bits.append(f"Candidate Intelligence rates technical strength {tech:.0f}/100")
    if isinstance(depth, (int, float)):
        bits.append(f"resume technical depth is {depth:.0f}/100")
    if bits:
        return "; ".join(bits) + " (resume quality, not a hiring score)."
    return "Technical evidence is limited in the current intelligence set."


def _leadership_potential(evidence: dict[str, Any]) -> str:
    """Restate leadership signal from timeline + intelligence."""
    intelligence = evidence.get("intelligence") or {}
    timeline = evidence.get("timeline") or {}
    lead = intelligence.get("leadership_score")
    progression = timeline.get("leadership_progression")
    bits: list[str] = []
    if isinstance(lead, (int, float)):
        bits.append(f"leadership signal {lead:.0f}/100 (Candidate Intelligence)")
    if progression:
        bits.append(f"trajectory: {progression} (Career Timeline Intelligence)")
    if bits:
        return "; ".join(bits) + "."
    return "Leadership potential is not strongly evidenced yet — validate in interview."


def _risk_overview(evidence: dict[str, Any]) -> str:
    """Restate the risk posture from the Risk engine + committee risks."""
    risk = evidence.get("risk") or {}
    level = risk.get("risk_level", "Unknown")
    flags = risk.get("red_flags") or []
    text = f"Overall risk is {level} (Resume Risk Detection)."
    if flags:
        text += " Red flags: " + "; ".join(flags[:3]) + "."
    else:
        text += " No red flags surfaced."
    committee = evidence.get("committee") or {}
    hiring_risks = (committee.get("decision") or {}).get("hiring_risks") or []
    if hiring_risks:
        text += " Committee-flagged risks: " + "; ".join(hiring_risks[:2]) + "."
    return text


def _interview_readiness(evidence: dict[str, Any]) -> str:
    """Restate interview readiness from the interview plan + recommendation."""
    interview = evidence.get("interview") or {}
    topics = (interview.get("technical_topics") or []) + (
        interview.get("system_design_topics") or []
    )
    recommendation = evidence.get("recommendation") or {}
    focus = recommendation.get("interview_focus") or []
    if topics or focus:
        lead = "A structured interview plan is available. "
        primary = topics[:3] or focus[:3]
        return lead + "Priority areas: " + "; ".join(primary) + " (Interview Intelligence)."
    return "No interview plan was generated; build one before proceeding."


def _executive_confidence(evidence: dict[str, Any]) -> tuple:
    """Return ``(label, note)`` qualitative confidence from the strongest source."""
    committee = evidence.get("committee") or {}
    overall = (committee.get("confidence") or {}).get("overall")
    source = "AI Hiring Committee"
    if overall is None:
        intelligence = evidence.get("intelligence") or {}
        overall = intelligence.get("confidence")
        source = "Candidate Intelligence engine"

    if not isinstance(overall, (int, float)):
        return "Moderate", "Confidence is moderate; evidence sources are partial."

    if overall >= 75:
        label = "High"
    elif overall >= 55:
        label = "Moderate"
    else:
        label = "Low"
    note = (
        f"Executive confidence is {label} ({overall:.0f}/100 per the {source}); "
        "this reflects evidence coverage and consensus, not a hiring score."
    )
    if label == "Low":
        note += " Evidence is thin — validate before acting."
    return label, note


def _top_reasons(evidence: dict[str, Any]) -> list[str]:
    """Collect the strongest evidence-backed reasons to proceed."""
    reasons: list[str] = []
    recommendation = evidence.get("recommendation") or {}
    reasons.extend(recommendation.get("reasons") or [])
    intelligence = evidence.get("intelligence") or {}
    reasons.extend(intelligence.get("strengths") or [])
    timeline = evidence.get("timeline") or {}
    reasons.extend(timeline.get("strengths") or [])
    # De-duplicate, preserve order, cap at 5.
    return list(dict.fromkeys(r for r in reasons if r))[:5]


def _top_concerns(evidence: dict[str, Any]) -> list[str]:
    """Collect the most material evidence-backed concerns."""
    concerns: list[str] = []
    risk = evidence.get("risk") or {}
    concerns.extend(risk.get("red_flags") or [])
    recommendation = evidence.get("recommendation") or {}
    concerns.extend(recommendation.get("concerns") or [])
    intelligence = evidence.get("intelligence") or {}
    concerns.extend(intelligence.get("weaknesses") or [])
    return list(dict.fromkeys(c for c in concerns if c))[:5]


def compose_executive_narrative(evidence: dict[str, Any]) -> dict[str, Any]:
    """Deterministically compose an :class:`ExecutiveNarrative` from evidence."""
    recommendation, rec_source = _headline_recommendation(evidence)
    conf_label, conf_note = _executive_confidence(evidence)

    overview = _overview_line(evidence)
    committee = evidence.get("committee") or {}
    chair_summary = (committee.get("decision") or {}).get("executive_summary", "")

    if chair_summary:
        summary = (
            f"{overview}. The recommendation is **{recommendation}** "
            f"(per the {rec_source}). {_first_sentences(chair_summary, 2)}"
        )
    else:
        summary = (
            f"{overview}. Synthesizing the resume, role, risk and intelligence "
            f"evidence, the recommendation is **{recommendation}** "
            f"(per the {rec_source})."
        )

    return {
        "executive_summary": summary,
        "overall_recommendation": recommendation,
        "business_impact": _business_impact(evidence),
        "technical_impact": _technical_impact(evidence),
        "leadership_potential": _leadership_potential(evidence),
        "risk_overview": _risk_overview(evidence),
        "interview_readiness": _interview_readiness(evidence),
        "executive_confidence": conf_label,
        "top_reasons": _top_reasons(evidence),
        "top_concerns": _top_concerns(evidence),
        "confidence_note": conf_note,
    }
