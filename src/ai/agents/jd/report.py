"""Report builders + improvement generator (Modules 2, 4, 5, 6, 10).

Pure functions that turn the deterministic *evidence dict* (document + metrics)
into the narrative sub-reports of a :class:`JDAnalysis`. They restate and
organize evidence — never introducing a fact absent from the evidence. Every
inference-bearing report carries a **confidence** (Modules 4, 17). The composer
calls these; keeping them here keeps the composer thin and each report testable.

Register convention (Module 17): observations are framed as **inference**
("suggests", "indicates"); the improvement plan is **suggestion**; both are
distinct from the **evidence** they cite.
"""

from __future__ import annotations

from typing import Any

SECTION_LABELS = {
    "title": "Job Title",
    "department": "Department",
    "employment_type": "Employment Type",
    "location": "Location",
    "remote_policy": "Remote Policy",
    "experience": "Experience",
    "education": "Education",
    "responsibilities": "Responsibilities",
    "requirements": "Requirements",
    "preferred_skills": "Preferred Skills",
    "benefits": "Benefits",
    "compensation": "Compensation",
    "company_info": "Company Information",
}

_SENIORITY = [
    "intern",
    "junior",
    "associate",
    "mid",
    "engineer",
    "senior",
    "staff",
    "lead",
    "principal",
    "manager",
    "director",
    "vp",
    "head",
    "chief",
    "architect",
]


def band(value: float) -> str:
    """Map a 0-100 quality dimension to a qualitative band."""
    if value >= 80:
        return "Excellent"
    if value >= 65:
        return "Strong"
    if value >= 50:
        return "Adequate"
    if value >= 35:
        return "Needs work"
    return "Weak"


def _labels(keys: list[str]) -> list[str]:
    """Map canonical section keys to display labels."""
    return [SECTION_LABELS.get(k, k) for k in keys]


def _has(blob: str, *cues: str) -> bool:
    """Return whether any cue is present in the JD blob."""
    return any(cue in blob for cue in cues)


# ---------------------------------------------------------------------------
# Structure (Module 1)
# ---------------------------------------------------------------------------


def build_structure(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the structure report from the evidence dict."""
    doc = ev.get("document", {})
    present = doc.get("sections_present", [])
    missing = doc.get("sections_empty", [])
    weak: list[str] = []
    if not doc.get("responsibilities"):
        weak.append("Responsibilities")
    if not doc.get("requirements"):
        weak.append("Requirements")
    if not doc.get("compensation"):
        weak.append("Compensation")
    observations = [f"{len(present)}/13 canonical JD sections detected."]
    if missing:
        observations.append("Absent: " + ", ".join(_labels(missing)) + ".")
    return {
        "sections_present": _labels(present),
        "sections_missing": _labels(missing),
        "weak_sections": weak,
        "observations": observations,
    }


# ---------------------------------------------------------------------------
# Role intelligence (Module 2)
# ---------------------------------------------------------------------------


def _seniority_rank(text: str) -> int:
    """Return a coarse seniority rank from a title/text."""
    low = text.lower()
    rank = -1
    for i, level in enumerate(_SENIORITY):
        if level in low:
            rank = max(rank, i)
    return rank


def build_role(ev: dict[str, Any]) -> dict[str, Any]:
    """Infer the role's real shape from the evidence dict (Module 2)."""
    doc = ev.get("document", {})
    metrics = ev.get("metrics", {})
    blob = (
        doc.get("title", "")
        + " "
        + " ".join(doc.get("responsibilities", []) + doc.get("requirements", []))
    ).lower()
    years = doc.get("years_experience")

    rank = _seniority_rank(doc.get("title", "") + " " + blob)
    if years is not None:
        seniority = "Senior+" if years >= 8 else ("Mid-level" if years >= 3 else "Junior")
    elif rank >= _SENIORITY.index("senior"):
        seniority = "Senior+"
    elif rank >= 0:
        seniority = "Mid-level"
    else:
        seniority = "Unspecified"

    leadership = _has(blob, "lead", "mentor", "manage", "coach", "guide the team")
    architecture = _has(
        blob, "architect", "system design", "design systems", "scalab", "distributed"
    )
    customer = _has(blob, "customer", "client", "stakeholder", "user-facing")
    management = _has(
        blob, "manage a team", "direct reports", "people management", "hire", "line manage"
    )
    cross = _has(
        blob, "cross-functional", "collaborate", "partner with", "work with product", "stakeholder"
    )
    decisions = _has(blob, "own", "drive", "decide", "responsible for", "strategy", "roadmap")

    confidence = 55.0 + (15 if years is not None else 0) + (10 if rank >= 0 else 0)
    observations = [
        f"Title '{doc.get('title', '?')}' + "
        f"{'stated ' + str(years) + 'y experience' if years is not None else 'no explicit experience bar'} "
        f"suggests a {seniority.lower()} role.",
    ]
    if metrics.get("architecture") or architecture:
        observations.append("Architecture/system-design responsibility is indicated.")

    return {
        "seniority": seniority,
        "technical_level": _tech_level(metrics, years),
        "ownership": "High" if decisions else "Moderate",
        "leadership_expectations": "Expected" if leadership else "Not emphasized",
        "decision_making": "Autonomous" if decisions else "Guided",
        "architecture_responsibility": "Yes" if architecture else "Limited/unclear",
        "customer_interaction": "Yes" if customer else "Minimal",
        "management_expectations": "People management" if management else "Individual contributor",
        "cross_functional": "Yes" if cross else "Not emphasized",
        "confidence": round(min(confidence, 90.0), 1),
        "observations": observations,
    }


def _tech_level(metrics: dict[str, Any], years) -> str:
    """Infer coarse technical level from tech breadth + experience."""
    count = metrics.get("tech_count", 0)
    if (years or 0) >= 8 or count >= 12:
        return "Deep / specialist"
    if (years or 0) >= 3 or count >= 6:
        return "Solid / working proficiency"
    return "Foundational"


# ---------------------------------------------------------------------------
# Technical intelligence (Module 3)
# ---------------------------------------------------------------------------


def build_technical(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the technical requirement report from the evidence dict."""
    m = ev.get("metrics", {})
    modern = m.get("modern_tech", [])
    dated = m.get("dated_tech", [])
    maturity = (
        "Modern"
        if modern and not dated
        else ("Mixed" if modern and dated else ("Legacy-leaning" if dated else "Unspecified"))
    )
    diversity = (
        "High"
        if m.get("tech_count", 0) >= 12
        else ("Moderate" if m.get("tech_count", 0) >= 6 else "Focused")
    )
    observations = []
    if modern:
        observations.append("Modern stack: " + ", ".join(modern[:8]) + ".")
    if dated:
        observations.append("Legacy technologies present: " + ", ".join(dated) + ".")
    if m.get("tech_count", 0) >= 15:
        observations.append(
            "Very broad tech list — inference: role may be under-scoped or a 'unicorn' ask."
        )
    return {
        "languages": m.get("languages", []),
        "frameworks": m.get("frameworks", []),
        "cloud": m.get("cloud", []),
        "ai_ml": m.get("ai_ml", []),
        "devops": m.get("devops", []),
        "data": m.get("data", []),
        "security": m.get("security", []),
        "infrastructure": m.get("infrastructure", []),
        "architecture": m.get("architecture", []),
        "technology_maturity": maturity,
        "technology_diversity": diversity,
        "observations": observations,
    }


# ---------------------------------------------------------------------------
# Hiring intent (Module 4) — every inference carries confidence
# ---------------------------------------------------------------------------

_INTENT_CUES = {
    "Growth hiring": (
        ("grow", "growing", "expand", "scaling the team", "new team", "build a team", "scale up"),
        "Language about team/company growth.",
    ),
    "Replacement hiring": (
        ("backfill", "replace", "vacancy", "departing"),
        "Explicit backfill/replacement language.",
    ),
    "Innovation hiring": (
        (
            "greenfield",
            "0 to 1",
            "zero to one",
            "new product",
            "innovat",
            "research",
            "prototype",
            "cutting edge",
        ),
        "New-product / greenfield / innovation language.",
    ),
    "Platform modernization": (
        (
            "modernize",
            "migrate",
            "legacy",
            "re-platform",
            "refactor",
            "rearchitect",
            "modernization",
        ),
        "Modernization / migration language.",
    ),
    "Digital transformation": (
        ("transformation", "digitize", "digital transformation", "cloud migration"),
        "Transformation language.",
    ),
    "Cost optimization": (
        ("cost optimization", "efficiency", "reduce cost", "optimize spend", "consolidat"),
        "Cost/efficiency language.",
    ),
}


def build_hiring_intent(ev: dict[str, Any]) -> dict[str, Any]:
    """Infer why the role is open, with confidence per signal (Module 4)."""
    doc = ev.get("document", {})
    blob = (
        ev.get("text_blob")
        or " ".join(
            [doc.get("title", ""), doc.get("company_info", "")]
            + doc.get("responsibilities", [])
            + doc.get("requirements", [])
        ).lower()
    )

    signals: list[dict[str, Any]] = []
    for intent, (cues, rationale) in _INTENT_CUES.items():
        hits = [c for c in cues if c in blob]
        if hits:
            confidence = min(85.0, 45.0 + len(hits) * 12.0)
            signals.append(
                {
                    "intent": intent,
                    "rationale": f"{rationale} (matched: {', '.join(hits)})",
                    "confidence": round(confidence, 1),
                }
            )

    if not signals:
        signals.append(
            {
                "intent": "Capacity hiring",
                "rationale": "No explicit intent cues; likely adding capacity to an existing function.",
                "confidence": 35.0,
            }
        )

    signals.sort(key=lambda s: s["confidence"], reverse=True)
    primary = signals[0]["intent"]
    priorities = _business_priorities(blob)
    summary = (
        f"Primary hiring intent appears to be **{primary}** "
        f"({signals[0]['confidence']:.0f}% confidence). This is inference from JD "
        f"language, not a stated fact."
    )
    return {
        "primary_intent": primary,
        "summary": summary,
        "signals": signals,
        "business_priorities": priorities,
        "confidence": signals[0]["confidence"],
    }


def _business_priorities(blob: str) -> list[str]:
    """Extract coarse business priorities from JD language."""
    priorities = []
    mapping = {
        "Scale & reliability": ("scale", "reliability", "uptime", "high availability", "latency"),
        "Speed of delivery": ("ship", "fast", "velocity", "deliver", "iterate"),
        "Product innovation": ("new product", "innovat", "greenfield", "0 to 1"),
        "Customer impact": ("customer", "user", "client"),
        "Security & compliance": ("security", "compliance", "gdpr", "soc2"),
    }
    for label, cues in mapping.items():
        if any(c in blob for c in cues):
            priorities.append(label)
    return priorities


# ---------------------------------------------------------------------------
# Organization intelligence (Module 5)
# ---------------------------------------------------------------------------

_ORG_CUES = {
    "Startup": (
        "startup",
        "early-stage",
        "seed",
        "series a",
        "fast-paced",
        "wear many hats",
        "founding",
    ),
    "Scale-up": ("series b", "series c", "hyper-growth", "scale-up", "scaleup", "scaling rapidly"),
    "Enterprise": (
        "enterprise",
        "fortune",
        "global",
        "large-scale",
        "multinational",
        "established",
    ),
    "Consulting": ("consulting", "consultancy", "client engagement", "clients"),
    "Research": ("research", "phd", "publications", "novel", "laboratory"),
    "Finance": ("bank", "fintech", "trading", "financial services", "payments"),
    "Healthcare": ("health", "clinical", "patient", "medical", "hospital"),
    "E-commerce": ("e-commerce", "ecommerce", "marketplace", "retail", "shopping"),
    "Government": ("government", "public sector", "clearance", "federal"),
    "Manufacturing": ("manufacturing", "factory", "supply chain", "industrial"),
    "Product Company": ("product company", "saas", "platform", "our product"),
}


def build_organization(ev: dict[str, Any]) -> dict[str, Any]:
    """Estimate company type + maturity from the evidence dict (Module 5)."""
    doc = ev.get("document", {})
    m = ev.get("metrics", {})
    blob = ev.get("text_blob") or (
        (doc.get("company_info", "") + " " + doc.get("title", "")).lower()
    )

    scored = {label: sum(1 for c in cues if c in blob) for label, cues in _ORG_CUES.items()}
    best = max(scored, key=scored.get) if any(scored.values()) else "Unspecified"
    signals = [
        f"{label}: {', '.join(c for c in cues if c in blob)}"
        for label, cues in _ORG_CUES.items()
        if scored[label]
    ]

    tech_maturity = (
        "High"
        if m.get("modern_tech") and (m.get("devops") or m.get("cloud"))
        else ("Moderate" if m.get("all_technologies") else "Unclear")
    )
    eng_maturity = (
        "High"
        if (m.get("devops") and m.get("architecture"))
        else ("Moderate" if m.get("devops") or m.get("architecture") else "Unclear")
    )
    confidence = min(80.0, 40.0 + (max(scored.values()) if scored else 0) * 12.0)

    observations = [
        "Company type is inferred from JD language; verify against actual company profile."
    ]
    return {
        "company_type": best,
        "technology_maturity": tech_maturity,
        "engineering_maturity": eng_maturity,
        "signals": signals,
        "confidence": round(confidence, 1),
        "observations": observations,
    }


# ---------------------------------------------------------------------------
# Requirement hierarchy (Module 6)
# ---------------------------------------------------------------------------

_MANDATORY_CUES = (
    "must",
    "required",
    "strong",
    "solid",
    "proven",
    "expert",
    "essential",
    "minimum",
    "years",
)
_PREFERRED_CUES = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "bonus",
    "plus",
    "good to have",
    "desirable",
    "ideally",
    "familiarity",
)


def build_requirement_hierarchy(ev: dict[str, Any]) -> dict[str, Any]:
    """Separate requirements into mandatory / preferred / hidden tiers (Module 6)."""
    doc = ev.get("document", {})
    reqs = list(doc.get("requirements", []))
    preferred_section = list(doc.get("preferred", []))
    responsibilities = list(doc.get("responsibilities", []))

    mandatory: list[str] = []
    preferred: list[str] = list(preferred_section)
    nice: list[str] = []
    optional: list[str] = []

    for line in reqs:
        low = line.lower()
        if any(c in low for c in _PREFERRED_CUES):
            preferred.append(line)
        elif any(c in low for c in _MANDATORY_CUES):
            mandatory.append(line)
        else:
            optional.append(line)

    # Everything with a "plus/bonus" tone is nice-to-have.
    nice = [p for p in preferred if any(c in p.lower() for c in ("bonus", "plus", "nice"))]

    hidden = _hidden_expectations(responsibilities, reqs)
    implicit = _implicit_requirements(ev)
    return {
        "mandatory": _dedupe(mandatory)[:15],
        "preferred": _dedupe(preferred)[:15],
        "nice_to_have": _dedupe(nice)[:10],
        "optional": _dedupe(optional)[:10],
        "hidden_expectations": hidden,
        "implicit_requirements": implicit,
    }


def _hidden_expectations(responsibilities: list[str], reqs: list[str]) -> list[str]:
    """Infer expectations implied by responsibilities but not stated as requirements."""
    blob = " ".join(responsibilities).lower()
    hidden = []
    if any(w in blob for w in ("mentor", "guide", "coach", "lead")):
        hidden.append("Leadership / mentoring is expected via responsibilities.")
    if any(w in blob for w in ("on-call", "oncall", "incident", "production support")):
        hidden.append("Operational / on-call ownership is implied.")
    if any(w in blob for w in ("stakeholder", "present", "communicate", "cross-functional")):
        hidden.append("Strong communication with stakeholders is implied.")
    if any(w in blob for w in ("architecture", "design", "scalab")):
        hidden.append("System-design capability is implied by the responsibilities.")
    return hidden


def _implicit_requirements(ev: dict[str, Any]) -> list[str]:
    """Infer requirements implied by the tech stack but not spelled out."""
    m = ev.get("metrics", {})
    implicit = []
    if m.get("ai_ml"):
        implicit.append("Solid ML/statistics fundamentals implied by the AI/ML stack.")
    if m.get("cloud") and not m.get("devops"):
        implicit.append("Basic CI/CD & infra-as-code likely expected alongside cloud.")
    if m.get("infrastructure"):
        implicit.append("Distributed-systems fundamentals implied by the infra requirements.")
    return implicit


def _dedupe(items: list[str]) -> list[str]:
    """Order-preserving dedupe."""
    seen: list[str] = []
    for i in items:
        if i and i not in seen:
            seen.append(i)
    return seen


# ---------------------------------------------------------------------------
# Improvement generator (Module 10)
# ---------------------------------------------------------------------------

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def generate_improvements(ev: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate prioritized JD improvement recommendations (Module 10)."""
    doc = ev.get("document", {})
    m = ev.get("metrics", {})
    dims = m.get("dimensions", {})
    improvements: list[dict[str, Any]] = []

    if not doc.get("requirements"):
        improvements.append(
            _imp(
                "Add explicit requirements",
                "Requirements",
                "high",
                "Recruiters cannot screen without clear qualifications.",
                "List 4-6 must-have qualifications.",
            )
        )
    if not doc.get("responsibilities"):
        improvements.append(
            _imp(
                "Add a responsibilities section",
                "Role Clarity",
                "high",
                "Candidates can't self-assess fit without day-to-day scope.",
                "Add 'What you'll do' with 4-6 bullets.",
            )
        )
    if not doc.get("preferred"):
        improvements.append(
            _imp(
                "Split mandatory vs preferred skills",
                "Requirement Quality",
                "high",
                "A flat list inflates the bar and shrinks the funnel.",
                "Separate 'Must have' from 'Nice to have'.",
            )
        )
    if not doc.get("compensation"):
        improvements.append(
            _imp(
                "Add a compensation range",
                "Hiring Readiness",
                "medium",
                "Comp transparency improves applies and reduces late-stage drop-off.",
                "Add a band, even if broad.",
            )
        )
    if m.get("tech_count", 0) >= 15:
        improvements.append(
            _imp(
                "Reduce technology overload",
                "Technical Clarity",
                "medium",
                "A long tech list reads as an unfillable 'unicorn' role.",
                "Keep 5-8 core technologies; move the rest to 'nice to have'.",
            )
        )
    if dims.get("role_clarity", 100) < 55:
        improvements.append(
            _imp(
                "Clarify ownership & success metrics",
                "Role Clarity",
                "medium",
                "Ownership and outcomes are unclear.",
                "Add 'success in 6 months looks like…'.",
            )
        )
    if m.get("vague_terms"):
        improvements.append(
            _imp(
                "Reduce ambiguity / filler",
                "Quality",
                "low",
                "Vague filler weakens clarity.",
                "Cut: " + ", ".join(m["vague_terms"]) + ".",
            )
        )
    if m.get("bias_terms"):
        improvements.append(
            _imp(
                "Improve inclusiveness",
                "Quality",
                "high",
                "Potentially biased/exclusionary language detected.",
                "Remove: " + ", ".join(m["bias_terms"]) + ".",
            )
        )
    if not (m.get("architecture")) and (doc.get("years_experience") or 0) >= 6:
        improvements.append(
            _imp(
                "Clarify architecture expectations",
                "Role Clarity",
                "low",
                "Senior role but architecture scope is unstated.",
                "State the system-design scope expected.",
            )
        )

    improvements.sort(key=lambda i: _PRIORITY_RANK.get(i["priority"], 3))
    return improvements


def _imp(title: str, area: str, priority: str, rationale: str, example: str) -> dict[str, Any]:
    """Build one improvement record."""
    impact = {"high": "High", "medium": "Medium", "low": "Low"}.get(priority, "Medium")
    return {
        "title": title,
        "area": area,
        "priority": priority,
        "impact": impact,
        "rationale": rationale,
        "example": example,
    }
