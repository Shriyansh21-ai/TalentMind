"""Resume extraction (Module 1 — structure parsing).

Turns a :class:`~src.models.candidates.Candidate` (and/or raw resume text) into a
normalized, deterministic :class:`ResumeDocument`. This is pure parsing — it
invents nothing; every field is copied or tokenized straight from the source.
Everything downstream (metrics, validators, composer) reasons only over this
document, which is what makes the whole agent hallucination-free offline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Canonical résumé sections we look for (Module 1).
CANONICAL_SECTIONS = [
    "contact_information",
    "professional_summary",
    "work_experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "achievements",
    "publications",
    "links",
]

# Section header cues for raw-text parsing.
_SECTION_CUES = {
    "professional_summary": ("summary", "objective", "profile", "about"),
    "work_experience": ("experience", "employment", "work history", "professional experience"),
    "projects": ("projects", "personal projects", "selected projects"),
    "skills": ("skills", "technical skills", "technologies", "tech stack"),
    "education": ("education", "academic"),
    "certifications": ("certification", "certificate", "licenses"),
    "achievements": ("achievement", "accomplishment", "awards", "honors"),
    "publications": ("publication", "research", "papers"),
    "links": ("links", "portfolio", "github", "linkedin", "website"),
}

_PROJECT_CUES = ("built", "designed", "developed", "architected", "created", "led", "launched", "implemented", "shipped")


@dataclass
class ResumeExperience:
    """One work-experience entry, normalized."""

    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: Optional[str] = None
    duration_months: int = 0
    is_current: bool = False
    industry: str = ""
    description: str = ""
    bullets: List[str] = field(default_factory=list)


@dataclass
class ResumeProject:
    """A project-like statement extracted from the resume."""

    name: str = ""
    text: str = ""
    source: str = ""  # where it came from (e.g. "work_experience:Acme")
    technologies: List[str] = field(default_factory=list)


@dataclass
class ResumeDocument:
    """A normalized, deterministic view of a resume.

    Nothing here is inferred — it is a faithful restatement of the source used by
    every analysis module as the sole factual input.
    """

    candidate_id: str = ""
    summary: str = ""
    headline: str = ""
    years_of_experience: float = 0.0
    experiences: List[ResumeExperience] = field(default_factory=list)
    projects: List[ResumeProject] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    skill_endorsements: Dict[str, int] = field(default_factory=dict)
    education: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    links: Dict[str, bool] = field(default_factory=dict)
    sections_present: List[str] = field(default_factory=list)
    sections_empty: List[str] = field(default_factory=list)
    bullets: List[str] = field(default_factory=list)
    raw_text: str = ""

    def all_text(self) -> str:
        """Return a single lowercase blob of every textual element."""
        parts = [self.summary, self.headline, " ".join(self.skills), self.raw_text]
        parts += [f"{e.title} {e.company} {e.description}" for e in self.experiences]
        parts += [p.text for p in self.projects]
        return " ".join(p for p in parts if p).lower()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the document."""
        return {
            "candidate_id": self.candidate_id,
            "summary": self.summary,
            "headline": self.headline,
            "years_of_experience": self.years_of_experience,
            "experiences": [vars(e) for e in self.experiences],
            "projects": [vars(p) for p in self.projects],
            "skills": self.skills,
            "skill_endorsements": self.skill_endorsements,
            "education": self.education,
            "certifications": self.certifications,
            "languages": self.languages,
            "links": self.links,
            "sections_present": self.sections_present,
            "sections_empty": self.sections_empty,
            "bullet_count": len(self.bullets),
        }


def _split_bullets(text: str) -> List[str]:
    """Split a free-text description into bullet-like statements."""
    if not text:
        return []
    # Split on newlines, bullet glyphs, and sentence terminators.
    pieces = re.split(r"[\n\r••;]|(?<=[.!?])\s+", text)
    return [p.strip(" -\t") for p in pieces if p and len(p.strip(" -\t")) > 2]


def _detect_projects(experiences: List[ResumeExperience], summary: str) -> List[ResumeProject]:
    """Detect project-like statements from experience bullets + summary."""
    projects: List[ResumeProject] = []
    pool = [("professional_summary", b) for b in _split_bullets(summary)]
    for exp in experiences:
        pool += [(f"work_experience:{exp.company}", b) for b in exp.bullets]
    for source, bullet in pool:
        low = bullet.lower()
        if any(cue in low for cue in _PROJECT_CUES):
            name = bullet.split(",")[0][:60]
            projects.append(ResumeProject(name=name, text=bullet, source=source))
    return projects[:12]


def from_candidate(candidate: Any, *, resume_text: str = "") -> ResumeDocument:
    """Build a :class:`ResumeDocument` from a :class:`Candidate`."""
    profile = candidate.profile
    doc = ResumeDocument(
        candidate_id=candidate.candidate_id,
        summary=profile.summary or "",
        headline=profile.headline or "",
        years_of_experience=float(profile.years_of_experience or 0.0),
        raw_text=resume_text or "",
    )

    for entry in candidate.career_history:
        bullets = _split_bullets(entry.description)
        doc.experiences.append(
            ResumeExperience(
                company=entry.company,
                title=entry.title,
                start_date=entry.start_date or "",
                end_date=entry.end_date,
                duration_months=int(entry.duration_months or 0),
                is_current=bool(entry.is_current),
                industry=entry.industry or "",
                description=entry.description or "",
                bullets=bullets,
            )
        )
        doc.bullets.extend(bullets)

    doc.bullets.extend(_split_bullets(doc.summary))
    doc.skills = [s.name for s in candidate.skills if s.name]
    doc.skill_endorsements = {s.name: int(s.endorsements or 0) for s in candidate.skills}
    doc.education = [
        {
            "institution": e.institution,
            "degree": e.degree,
            "field_of_study": e.field_of_study,
            "start_year": e.start_year,
            "end_year": e.end_year,
            "tier": e.tier,
        }
        for e in candidate.education
    ]
    doc.certifications = [c.name for c in candidate.certifications if getattr(c, "name", None)]
    doc.languages = [l.language for l in candidate.languages]

    signals = candidate.redrob_signals
    doc.links = {
        "github": bool(getattr(signals, "github_activity_score", 0) or 0) > 0,
        "linkedin": bool(getattr(signals, "linkedin_connected", False)),
        "verified_email": bool(getattr(signals, "verified_email", False)),
    }

    doc.projects = _detect_projects(doc.experiences, doc.summary)
    _mark_sections(doc)
    return doc


def _mark_sections(doc: ResumeDocument) -> None:
    """Populate ``sections_present`` / ``sections_empty`` from the document."""
    present: List[str] = []
    empty: List[str] = []

    checks = {
        "contact_information": bool(doc.links.get("verified_email") or doc.links.get("linkedin")),
        "professional_summary": bool(doc.summary.strip()),
        "work_experience": bool(doc.experiences),
        "projects": bool(doc.projects),
        "skills": bool(doc.skills),
        "education": bool(doc.education),
        "certifications": bool(doc.certifications),
        "achievements": _has_achievements(doc),
        "publications": _mentions(doc, ("publication", "paper", "research", "journal")),
        "links": bool(doc.links.get("github") or doc.links.get("linkedin")),
    }
    for section, ok in checks.items():
        (present if ok else empty).append(section)
    doc.sections_present = present
    doc.sections_empty = empty


def _has_achievements(doc: ResumeDocument) -> bool:
    """Return whether any quantified/recognition signal is present."""
    blob = doc.all_text()
    if re.search(r"\b\d+(\.\d+)?\s*%|\$\s*\d|\b\d{2,}\b", blob):
        return True
    return _mentions(doc, ("award", "recognition", "patent", "keynote", "speaker"))


def _mentions(doc: ResumeDocument, cues) -> bool:
    """Return whether any cue appears in the resume text."""
    blob = doc.all_text()
    return any(cue in blob for cue in cues)


def extract(candidate: Any = None, *, resume_text: str = "", candidate_id: str = "") -> ResumeDocument:
    """Public entry: build a document from a candidate and/or raw text."""
    if candidate is not None:
        return from_candidate(candidate, resume_text=resume_text)
    # Text-only fallback (future raw-resume ingestion): minimal structure parse.
    doc = ResumeDocument(candidate_id=candidate_id, raw_text=resume_text or "")
    doc.bullets = _split_bullets(resume_text)
    _mark_sections(doc)
    return doc
