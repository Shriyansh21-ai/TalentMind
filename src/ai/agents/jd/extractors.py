"""JD extraction (Module 1 — structure parsing).

Turns raw Job Description text into a normalized, deterministic
:class:`JDDocument`. This is pure parsing — it invents nothing (Module 17): every
field is copied or tokenized straight from the JD text. Everything downstream
(metrics, validators, report, composer) reasons only over this document, which is
what keeps the agent grounded in evidence.

The parser is section-aware (header cues) but degrades gracefully on free-form
text: if no headings are found, the whole body becomes the responsibilities /
requirements pool so analysis still runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Canonical JD sections we look for (Module 1).
CANONICAL_SECTIONS = [
    "title",
    "department",
    "employment_type",
    "location",
    "remote_policy",
    "experience",
    "education",
    "responsibilities",
    "requirements",
    "preferred_skills",
    "benefits",
    "compensation",
    "company_info",
]

# Header cues → canonical section. Matched case-insensitively against short lines.
_SECTION_CUES = {
    "responsibilities": (
        "responsibilities",
        "what you'll do",
        "what you will do",
        "the role",
        "duties",
        "day to day",
        "day-to-day",
    ),
    "requirements": (
        "requirements",
        "qualifications",
        "what we're looking for",
        "what we are looking for",
        "must have",
        "must-have",
        "you have",
        "required skills",
        "you'll need",
    ),
    "preferred_skills": (
        "preferred",
        "nice to have",
        "nice-to-have",
        "bonus",
        "good to have",
        "plus",
        "desirable",
    ),
    "benefits": ("benefits", "perks", "what we offer", "we offer"),
    "compensation": ("compensation", "salary", "pay", "ctc", "package"),
    "company_info": ("about us", "about the company", "who we are", "our company", "about "),
    "education": ("education", "academic"),
    "experience": ("experience required", "experience:", "years of experience"),
    "department": ("department", "team:", "function:"),
    "employment_type": ("employment type", "job type", "contract type"),
    "location": ("location", "based in", "office location"),
    "remote_policy": ("remote", "hybrid", "on-site", "onsite", "work from home", "wfh"),
}

_EMPLOYMENT_TYPES = (
    "full-time",
    "full time",
    "part-time",
    "part time",
    "contract",
    "internship",
    "temporary",
    "freelance",
)
_REMOTE_TERMS = (
    "remote",
    "hybrid",
    "on-site",
    "onsite",
    "work from home",
    "wfh",
    "in-office",
    "in office",
)
_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years|yrs|yr)")
_DEGREE_RE = re.compile(
    r"\b(bachelor|master|phd|b\.?tech|m\.?tech|b\.?s\.?|m\.?s\.?|mba|degree)\b", re.IGNORECASE
)
_MONEY_RE = re.compile(
    r"(\$\s?\d[\d,]*|\d+\s*(?:k|lpa|lakh|lac)\b|₹\s?\d|\beur\b|\busd\b|\binr\b)", re.IGNORECASE
)


@dataclass
class JDDocument:
    """A normalized, deterministic view of a Job Description.

    Nothing here is inferred — it is a faithful restatement of the JD text used
    by every analysis module as the sole factual input.
    """

    jd_id: str = ""
    title: str = ""
    department: str = ""
    employment_type: str = ""
    location: str = ""
    remote_policy: str = ""
    years_experience: int | None = None
    education: str = ""
    responsibilities: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    preferred: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    compensation: str = ""
    company_info: str = ""
    sections_present: list[str] = field(default_factory=list)
    sections_empty: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    raw_text: str = ""

    def all_text(self) -> str:
        """Return a single lowercase blob of the whole JD."""
        return self.raw_text.lower()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the document."""
        return {
            "jd_id": self.jd_id,
            "title": self.title,
            "department": self.department,
            "employment_type": self.employment_type,
            "location": self.location,
            "remote_policy": self.remote_policy,
            "years_experience": self.years_experience,
            "education": self.education,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "preferred": self.preferred,
            "benefits": self.benefits,
            "compensation": self.compensation,
            "company_info": self.company_info,
            "sections_present": self.sections_present,
            "sections_empty": self.sections_empty,
            "bullet_count": len(self.bullets),
        }


def _clean(line: str) -> str:
    """Strip bullet glyphs / whitespace from a line."""
    return line.strip(" \t-*•·°◦–—>").strip()


def _match_section(line: str) -> str | None:
    """Return the canonical section a short header line denotes, or ``None``."""
    low = line.lower().strip().rstrip(":")
    if len(low) > 60:  # headers are short; long lines are content
        return None
    for section, cues in _SECTION_CUES.items():
        for cue in cues:
            if low == cue or low.startswith(cue) or (len(low) <= 40 and cue in low):
                return section
    return None


def parse(jd_text: str, *, jd_id: str = "", title: str = "") -> JDDocument:
    """Parse raw JD text into a :class:`JDDocument`."""
    doc = JDDocument(jd_id=jd_id, raw_text=jd_text or "", title=title.strip())
    lines = [ln for ln in (jd_text or "").splitlines()]

    # First non-empty line is a good title guess when none supplied.
    if not doc.title:
        for ln in lines:
            if ln.strip():
                doc.title = _clean(ln)[:120]
                break

    current: str | None = None
    buckets: dict[str, list[str]] = {s: [] for s in CANONICAL_SECTIONS}
    body: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        section = _match_section(line)
        if section is not None:
            current = section
            # Capture any trailing content on the header line (e.g. "Location: Remote").
            tail = line.split(":", 1)[1].strip() if ":" in line else ""
            if tail:
                buckets[section].append(_clean(tail))
            continue
        cleaned = _clean(line)
        if cleaned:
            body.append(cleaned)
            if current:
                buckets[current].append(cleaned)

    doc.bullets = body

    # Section content.
    doc.responsibilities = buckets["responsibilities"]
    doc.requirements = buckets["requirements"]
    doc.preferred = buckets["preferred_skills"]
    doc.benefits = buckets["benefits"]
    doc.company_info = " ".join(buckets["company_info"])[:600]

    # If no explicit responsibilities/requirements headers were found, treat the
    # whole body as a shared pool so analysis still has material.
    if not doc.responsibilities and not doc.requirements and body:
        doc.requirements = body

    blob = doc.all_text()

    # Scalar fields.
    doc.employment_type = next((t for t in _EMPLOYMENT_TYPES if t in blob), "")
    doc.remote_policy = next((t for t in _REMOTE_TERMS if t in blob), "")
    doc.department = " ".join(buckets["department"])[:80]
    doc.location = " ".join(buckets["location"])[:80]

    years = _YEARS_RE.findall(blob)
    if years:
        try:
            doc.years_experience = max(int(y) for y in years)
        except ValueError:
            doc.years_experience = None

    degree = _DEGREE_RE.search(jd_text or "")
    doc.education = degree.group(0) if degree else " ".join(buckets["education"])[:80]

    # Compensation: only record what is literally present — never invent salary.
    comp_lines = buckets["compensation"]
    money = _MONEY_RE.search(" ".join(comp_lines) or "")
    if comp_lines:
        doc.compensation = " ".join(comp_lines)[:120]
    elif money:
        doc.compensation = money.group(0)

    _mark_sections(doc, blob)
    return doc


def _mark_sections(doc: JDDocument, blob: str) -> None:
    """Populate ``sections_present`` / ``sections_empty`` for the document."""
    checks = {
        "title": bool(doc.title),
        "department": bool(doc.department),
        "employment_type": bool(doc.employment_type),
        "location": bool(doc.location),
        "remote_policy": bool(doc.remote_policy),
        "experience": doc.years_experience is not None,
        "education": bool(doc.education),
        "responsibilities": bool(doc.responsibilities),
        "requirements": bool(doc.requirements),
        "preferred_skills": bool(doc.preferred),
        "benefits": bool(doc.benefits),
        "compensation": bool(doc.compensation),
        "company_info": bool(doc.company_info),
    }
    doc.sections_present = [s for s, ok in checks.items() if ok]
    doc.sections_empty = [s for s, ok in checks.items() if not ok]


def extract(jd_text: str = "", *, jd_id: str = "", title: str = "") -> JDDocument:
    """Public entry: build a :class:`JDDocument` from raw JD text."""
    return parse(jd_text or "", jd_id=jd_id, title=title)
