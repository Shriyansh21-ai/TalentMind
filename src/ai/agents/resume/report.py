"""Report builders + improvement generator (Modules 3, 5, 6, 9, 10).

Pure functions that turn the deterministic *evidence dict* (document + metrics +
risks) into the narrative sub-reports that make up a :class:`ResumeAnalysis`.
They restate and organize evidence — they never introduce a fact that is not in
the evidence. The composer calls these; keeping them here keeps the composer
thin and each report independently testable.

Language convention (Module 17): observations are framed as **inference**
("suggests", "indicates") and the improvement plan as **suggestion**, distinct
from the underlying **evidence** they cite.
"""

from __future__ import annotations

from typing import Any

SECTION_LABELS = {
    "contact_information": "Contact Information",
    "professional_summary": "Professional Summary",
    "work_experience": "Work Experience",
    "projects": "Projects",
    "skills": "Skills",
    "education": "Education",
    "certifications": "Certifications",
    "achievements": "Achievements",
    "publications": "Publications",
    "links": "Links / Portfolio",
}


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


# ---------------------------------------------------------------------------
# Structure (Module 1)
# ---------------------------------------------------------------------------


def build_structure(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the structure report from the evidence dict."""
    doc = ev.get("document", {})
    metrics = ev.get("metrics", {})
    present = doc.get("sections_present", [])
    empty = doc.get("sections_empty", [])

    weak: list[str] = []
    if not doc.get("summary", "").strip():
        weak.append("Professional Summary")
    if (
        metrics.get("bullet_count", 0)
        and metrics.get("action_verb_bullets", 0) / max(metrics["bullet_count"], 1) < 0.3
    ):
        weak.append("Work Experience (few action verbs)")
    if doc.get("projects") == [] or not doc.get("projects"):
        weak.append("Projects")

    observations = [
        f"{len(present)}/10 canonical sections detected.",
    ]
    if empty:
        observations.append("Absent/empty: " + ", ".join(_labels(empty)) + ".")
    return {
        "sections_present": _labels(present),
        "sections_missing": _labels(empty),
        "weak_sections": weak,
        "empty_sections": _labels(empty),
        "observations": observations,
    }


# ---------------------------------------------------------------------------
# Career story (Module 3)
# ---------------------------------------------------------------------------


def build_career_story(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the career-story report from the evidence dict."""
    doc = ev.get("document", {})
    metrics = ev.get("metrics", {})
    experiences = doc.get("experiences", [])
    dims = metrics.get("dimensions", {})
    titles = [e.get("title", "") for e in experiences]

    industries = {e.get("industry", "") for e in experiences if e.get("industry")}
    consistency = (
        "Focused" if len(industries) <= 1 else ("Cohesive" if len(industries) == 2 else "Broad")
    )
    direction = _direction(titles)
    focus = "Specialist" if len(set(doc.get("skills", []))) <= 12 else "Generalist"
    progression = band(dims.get("career_narrative", 45))

    narrative = (
        f"{len(experiences)} role(s) over ~{doc.get('years_of_experience', 0):.0f} years; "
        f"{direction.lower()} trajectory with a {consistency.lower()} industry footprint."
    )
    observations = []
    if titles:
        observations.append(f"Most recent role: {titles[0]}.")
    observations.append(
        f"Progression reads as {progression.lower()} based on title seniority over time."
    )
    return {
        "narrative": narrative,
        "direction": direction,
        "growth": progression,
        "consistency": consistency,
        "focus": focus,
        "progression_strength": progression,
        "observations": observations,
    }


def _direction(titles: list[str]) -> str:
    """Infer coarse career direction from title ordering (newest first)."""
    from src.ai.agents.resume.metrics import _seniority_rank

    if len(titles) < 2:
        return "Early-stage"
    if _seniority_rank(titles[0]) > _seniority_rank(titles[-1]):
        return "Upward"
    if _seniority_rank(titles[0]) == _seniority_rank(titles[-1]):
        return "Lateral"
    return "Mixed"


# ---------------------------------------------------------------------------
# Technical (Module 4)
# ---------------------------------------------------------------------------


def build_technical(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the technical report from the evidence dict."""
    metrics = ev.get("metrics", {})
    modern = metrics.get("modern_tech", [])
    dated = metrics.get("dated_tech", [])
    diversity = (
        "High"
        if metrics.get("skill_count", 0) >= 12
        else ("Moderate" if metrics.get("skill_count", 0) >= 6 else "Narrow")
    )
    depth = band(metrics.get("dimensions", {}).get("technical_depth", 40))

    observations = []
    if modern:
        observations.append("Modern stack present: " + ", ".join(modern[:8]) + ".")
    if dated:
        observations.append(
            "Older technologies present: " + ", ".join(dated) + " (verify current relevance)."
        )
    if not metrics.get("production_exposure"):
        observations.append(
            "Limited explicit production/scale language — inference only, worth confirming."
        )
    return {
        "technologies": metrics.get("technologies", []),
        "modern_technologies": modern,
        "dated_technologies": dated,
        "diversity": diversity,
        "depth": depth,
        "breadth": diversity,
        "cloud_exposure": bool(metrics.get("cloud_exposure")),
        "ai_exposure": bool(metrics.get("ai_exposure")),
        "production_exposure": bool(metrics.get("production_exposure")),
        "open_source": bool(metrics.get("open_source")),
        "observations": observations,
    }


# ---------------------------------------------------------------------------
# Projects (Module 5)
# ---------------------------------------------------------------------------


def build_projects(ev: dict[str, Any]) -> list[dict[str, Any]]:
    """Build per-project intelligence from the evidence dict."""
    doc = ev.get("document", {})
    metrics = ev.get("metrics", {})
    projects = doc.get("projects", [])
    insights: list[dict[str, Any]] = []
    for proj in projects[:8]:
        text = proj.get("text", "")
        low = text.lower()
        word_count = len(text.split())
        complexity = "High" if word_count >= 18 else ("Medium" if word_count >= 9 else "Low")
        quantified = any(ch.isdigit() for ch in text)
        leadership = any(cue in low for cue in ("led", "owned", "mentored", "spearheaded"))
        production = any(
            cue in low for cue in ("production", "scale", "users", "latency", "uptime")
        )
        techs = [t for t in metrics.get("modern_tech", []) if t in low]
        insights.append(
            {
                "name": proj.get("name", "Project"),
                "complexity": complexity,
                "business_value": "Evident" if quantified else "Unclear (not quantified)",
                "innovation": "Notable"
                if any(w in low for w in ("novel", "first", "new", "innovat"))
                else "Standard",
                "impact": "Quantified" if quantified else "Not quantified",
                "production_readiness": "Production-grade" if production else "Unspecified",
                "uniqueness": "Distinctive" if techs else "Common",
                "scalability": "Addressed" if production else "Not described",
                "technologies": techs,
                "evidence": text[:200],
            }
        )
    return insights


# ---------------------------------------------------------------------------
# Achievements (Module 6)
# ---------------------------------------------------------------------------


def build_achievements(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the achievement report from the evidence dict."""
    metrics = ev.get("metrics", {})
    quantified = metrics.get("quantified_statements", [])
    leadership = metrics.get("leadership_statements", [])
    recognition = metrics.get("recognition_statements", [])

    missing: list[str] = []
    if not quantified:
        missing.append("Quantified business impact (%, $, scale, time saved).")
    if not leadership:
        missing.append("Explicit leadership/ownership statements.")
    if not recognition:
        missing.append("Awards, patents, publications or public speaking.")

    suggestions = []
    if not quantified:
        suggestions.append("Add metrics to at least 3 bullets (e.g. 'reduced latency 40%').")
    if not leadership and not missing == []:
        suggestions.append("Surface scope: team size led, systems owned, budget influenced.")

    strength = band(metrics.get("dimensions", {}).get("achievements", 25))
    return {
        "quantified": quantified[:8],
        "leadership": leadership[:6],
        "recognition": recognition[:6],
        "strength": strength,
        "missing": missing,
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# ATS (Module 7)
# ---------------------------------------------------------------------------


def build_ats(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the ATS optimization report from the evidence dict."""
    metrics = ev.get("metrics", {})
    doc = ev.get("document", {})
    dims = metrics.get("dimensions", {})
    friendliness = band(dims.get("ats_friendliness", 45))

    parsing_notes = []
    if len(doc.get("sections_present", [])) < 6:
        parsing_notes.append(
            "Fewer than 6 standard sections detected — add clear section headings."
        )
    if metrics.get("overused_keywords"):
        parsing_notes.append(
            "Some terms are heavily repeated: " + ", ".join(metrics["overused_keywords"]) + "."
        )
    if not parsing_notes:
        parsing_notes.append("Standard sections present; structure is parseable.")

    suggestions = []
    if metrics.get("missing_keywords"):
        suggestions.append(
            "Consider adding role-relevant keywords: "
            + ", ".join(metrics["missing_keywords"][:10])
            + "."
        )
    if metrics.get("overused_keywords"):
        suggestions.append("Vary phrasing to reduce keyword repetition.")
    return {
        "friendliness": friendliness,
        "matched_keywords": metrics.get("matched_keywords", []),
        "missing_keywords": metrics.get("missing_keywords", []),
        "overused_keywords": metrics.get("overused_keywords", []),
        "parsing_notes": parsing_notes,
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# Writing (Module 9)
# ---------------------------------------------------------------------------


def build_writing(ev: dict[str, Any]) -> dict[str, Any]:
    """Build the writing report + sample rewrites from the evidence dict."""
    metrics = ev.get("metrics", {})
    bullet_count = metrics.get("bullet_count", 0)
    verb_ratio = (metrics.get("action_verb_bullets", 0) / bullet_count) if bullet_count else 0.0
    avg_words = metrics.get("avg_bullet_words", 0.0)

    tone = "Professional" if not metrics.get("buzzword_hits") else "Buzzword-heavy"
    clarity = "Clear" if 8 <= avg_words <= 28 else ("Verbose" if avg_words > 28 else "Terse")
    conciseness = "Concise" if avg_words <= 28 else "Wordy"
    verb_usage = "Strong" if verb_ratio >= 0.5 else ("Moderate" if verb_ratio >= 0.3 else "Weak")
    bullet_quality = band(metrics.get("dimensions", {}).get("writing", 40))

    observations = [
        f"~{avg_words:.0f} words/bullet across {bullet_count} bullet(s); action-verb usage {verb_usage.lower()}.",
    ]
    if metrics.get("buzzword_hits"):
        observations.append("Buzzwords weaken impact: " + ", ".join(metrics["buzzword_hits"]) + ".")

    rewrites = _sample_rewrites(ev)
    return {
        "tone": tone,
        "clarity": clarity,
        "conciseness": conciseness,
        "action_verb_usage": verb_usage,
        "bullet_quality": bullet_quality,
        "observations": observations,
        "sample_rewrites": rewrites,
    }


def _sample_rewrites(ev: dict[str, Any]) -> list[dict[str, str]]:
    """Produce concrete before/after rewrites from weak bullets in evidence."""
    doc = ev.get("document", {})
    rewrites: list[dict[str, str]] = []
    bullets = []
    for exp in doc.get("experiences", []):
        bullets.extend(exp.get("bullets", []))
    from src.ai.agents.resume.metrics import STRONG_ACTION_VERBS, WEAK_VERBS

    for bullet in bullets:
        low = bullet.lower()
        first = low.split()[0] if low.split() else ""
        weak = any(w in low for w in WEAK_VERBS) or first not in STRONG_ACTION_VERBS
        if weak and len(bullet.split()) >= 4:
            rewrites.append(
                {
                    "before": bullet[:160],
                    "after": "Led/Built/Improved <what> to achieve <quantified outcome> (add a metric).",
                    "reason": "Open with a strong action verb and end with a measurable result.",
                }
            )
        if len(rewrites) >= 3:
            break
    return rewrites


# ---------------------------------------------------------------------------
# Improvement generator (Module 10)
# ---------------------------------------------------------------------------

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def generate_improvements(ev: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate prioritized improvement recommendations (ranked by impact)."""
    metrics = ev.get("metrics", {})
    doc = ev.get("document", {})
    dims = metrics.get("dimensions", {})
    improvements: list[dict[str, Any]] = []

    if not metrics.get("quantified_statements"):
        improvements.append(
            {
                "title": "Quantify achievements",
                "area": "Achievements",
                "priority": "high",
                "impact": "High",
                "rationale": "No metrics detected; quantified impact is the single strongest recruiter signal.",
                "example": "‘Reduced API latency 45% (p95) serving 2M requests/day.’",
            }
        )
    if dims.get("writing", 100) < 55:
        improvements.append(
            {
                "title": "Rewrite bullets with strong action verbs",
                "area": "Writing",
                "priority": "high",
                "impact": "High",
                "rationale": "Low action-verb ratio / weak phrasing reduces perceived impact.",
                "example": "Replace ‘Responsible for X’ with ‘Led X, delivering Y’.",
            }
        )
    if not doc.get("summary", "").strip():
        improvements.append(
            {
                "title": "Add a professional summary",
                "area": "Structure",
                "priority": "medium",
                "impact": "Medium",
                "rationale": "No summary section; recruiters read it first.",
                "example": "3-line summary: seniority, domain, headline achievement.",
            }
        )
    if metrics.get("missing_keywords"):
        improvements.append(
            {
                "title": "Improve ATS keyword coverage",
                "area": "ATS",
                "priority": "medium",
                "impact": "Medium",
                "rationale": "Role-relevant keywords are missing, hurting searchability.",
                "example": "Weave in: " + ", ".join(metrics["missing_keywords"][:6]) + ".",
            }
        )
    if dims.get("technical_depth", 100) < 55:
        improvements.append(
            {
                "title": "Deepen technical evidence",
                "area": "Technical",
                "priority": "medium",
                "impact": "Medium",
                "rationale": "Technical depth reads thin; show architecture/scale decisions.",
                "example": "Describe a system you designed: scale, trade-offs, outcome.",
            }
        )
    if not metrics.get("leadership_statements"):
        improvements.append(
            {
                "title": "Add leadership evidence",
                "area": "Achievements",
                "priority": "low",
                "impact": "Medium",
                "rationale": "No ownership/leadership language detected.",
                "example": "‘Mentored 4 engineers; owned the billing service end-to-end.’",
            }
        )
    if metrics.get("buzzword_hits"):
        improvements.append(
            {
                "title": "Reduce buzzwords",
                "area": "Professionalism",
                "priority": "low",
                "impact": "Low",
                "rationale": "Generic buzzwords dilute concrete evidence.",
                "example": "Cut: " + ", ".join(metrics["buzzword_hits"]) + ".",
            }
        )

    improvements.sort(key=lambda i: _PRIORITY_RANK.get(i["priority"], 3))
    return improvements
