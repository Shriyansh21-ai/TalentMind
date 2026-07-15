"""Resume metrics (Modules 2, 4, 6, 7, 11).

Deterministic, evidence-derived measurements over a :class:`ResumeDocument`:
writing quality, technical coverage, achievements, ATS keywords — and the
resume-quality **dimensions** (0-100). These numbers describe *resume quality*
only and must never influence hiring ranking (Module 11).

Every number here is a transparent function of counts found in the resume, so it
is reproducible and explainable — no model, no randomness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from src.ai.agents.resume.extractors import ResumeDocument

# -- vocabularies (small, transparent, editable) ----------------------------

STRONG_ACTION_VERBS = {
    "led", "built", "designed", "architected", "developed", "launched", "shipped",
    "improved", "increased", "reduced", "optimized", "scaled", "delivered",
    "created", "implemented", "drove", "owned", "mentored", "spearheaded",
    "automated", "migrated", "founded", "established", "accelerated", "streamlined",
}

WEAK_VERBS = {"responsible", "worked", "helped", "assisted", "involved", "participated", "handled"}

BUZZWORDS = {
    "synergy", "go-getter", "hardworking", "team player", "results-driven",
    "detail-oriented", "passionate", "guru", "ninja", "rockstar", "self-starter",
    "dynamic", "proactive", "thought leader", "wizard", "hard worker",
}

MODERN_TECH = {
    "python", "go", "golang", "rust", "typescript", "react", "kubernetes", "docker",
    "terraform", "aws", "gcp", "azure", "kafka", "spark", "airflow", "snowflake",
    "pytorch", "tensorflow", "llm", "rag", "langchain", "transformers", "graphql",
    "fastapi", "grpc", "kotlin", "swift", "next.js", "vector", "faiss",
}

DATED_TECH = {
    "jquery", "perl", "cobol", "vb6", "flash", "silverlight", "asp classic",
    "coldfusion", "svn", "soap", "actionscript", "backbone", "angularjs",
}

CLOUD_TECH = {"aws", "gcp", "azure", "cloud", "kubernetes", "terraform", "lambda", "ec2", "s3"}
AI_TECH = {"machine learning", "deep learning", "ml", "ai", "nlp", "llm", "rag", "pytorch", "tensorflow", "transformers", "computer vision"}
PRODUCTION_CUES = {"production", "scale", "scalable", "reliability", "uptime", "latency", "throughput", "sla", "high availability"}
OSS_CUES = {"open source", "open-source", "maintainer", "contributor", "github", "npm package", "pypi"}

LEADERSHIP_CUES = {"led", "mentored", "managed", "owned", "spearheaded", "founded", "headed", "directed", "coordinated"}
RECOGNITION_CUES = {"award", "recognition", "patent", "keynote", "speaker", "published", "winner", "finalist"}

_QUANT_RE = re.compile(r"(\d+(\.\d+)?\s*%|\$\s?\d[\d,]*|\b\d{2,}\b|\b\d+x\b)")
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-]*")


@dataclass
class ResumeMetrics:
    """A bundle of deterministic resume measurements + quality dimensions."""

    bullet_count: int = 0
    action_verb_bullets: int = 0
    weak_verb_bullets: int = 0
    quantified_bullets: int = 0
    avg_bullet_words: float = 0.0
    buzzword_hits: List[str] = field(default_factory=list)
    redundant_phrases: List[str] = field(default_factory=list)
    # technical
    technologies: List[str] = field(default_factory=list)
    modern_tech: List[str] = field(default_factory=list)
    dated_tech: List[str] = field(default_factory=list)
    cloud_exposure: bool = False
    ai_exposure: bool = False
    production_exposure: bool = False
    open_source: bool = False
    skill_count: int = 0
    tech_dumping: bool = False
    # achievements
    quantified_statements: List[str] = field(default_factory=list)
    leadership_statements: List[str] = field(default_factory=list)
    recognition_statements: List[str] = field(default_factory=list)
    # ats
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    overused_keywords: List[str] = field(default_factory=list)
    # dimensions (0-100) — resume quality ONLY
    dimensions: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable dict of the metrics."""
        return {
            "bullet_count": self.bullet_count,
            "action_verb_bullets": self.action_verb_bullets,
            "weak_verb_bullets": self.weak_verb_bullets,
            "quantified_bullets": self.quantified_bullets,
            "avg_bullet_words": round(self.avg_bullet_words, 1),
            "buzzword_hits": self.buzzword_hits,
            "redundant_phrases": self.redundant_phrases,
            "technologies": self.technologies,
            "modern_tech": self.modern_tech,
            "dated_tech": self.dated_tech,
            "cloud_exposure": self.cloud_exposure,
            "ai_exposure": self.ai_exposure,
            "production_exposure": self.production_exposure,
            "open_source": self.open_source,
            "skill_count": self.skill_count,
            "tech_dumping": self.tech_dumping,
            "quantified_statements": self.quantified_statements,
            "leadership_statements": self.leadership_statements,
            "recognition_statements": self.recognition_statements,
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "overused_keywords": self.overused_keywords,
            "dimensions": {k: round(v, 1) for k, v in self.dimensions.items()},
        }


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp ``value`` into ``[low, high]``."""
    return max(low, min(high, value))


def _first_word(text: str) -> str:
    """Return the lowercase first word of ``text``."""
    match = _WORD_RE.search(text.lower())
    return match.group(0) if match else ""


def compute_metrics(doc: ResumeDocument, *, jd: str = "") -> ResumeMetrics:
    """Compute the full metric bundle for ``doc`` (optionally against a JD)."""
    m = ResumeMetrics()
    bullets = [b for b in doc.bullets if b]
    m.bullet_count = len(bullets)

    word_total = 0
    verb_counter: Dict[str, int] = {}
    for bullet in bullets:
        low = bullet.lower()
        words = _WORD_RE.findall(low)
        word_total += len(words)
        first = _first_word(bullet)
        verb_counter[first] = verb_counter.get(first, 0) + 1
        if first in STRONG_ACTION_VERBS:
            m.action_verb_bullets += 1
        if any(w in low for w in WEAK_VERBS):
            m.weak_verb_bullets += 1
        if _QUANT_RE.search(bullet):
            m.quantified_bullets += 1
            m.quantified_statements.append(bullet)
        if any(cue in low for cue in LEADERSHIP_CUES):
            m.leadership_statements.append(bullet)
        if any(cue in low for cue in RECOGNITION_CUES):
            m.recognition_statements.append(bullet)

    m.avg_bullet_words = (word_total / m.bullet_count) if m.bullet_count else 0.0

    blob = doc.all_text()
    m.buzzword_hits = sorted({b for b in BUZZWORDS if b in blob})
    m.redundant_phrases = sorted(
        {v for v, c in verb_counter.items() if v and c >= 3 and v not in ("", "the", "a")}
    )[:5]

    # -- technical ----------------------------------------------------------
    skills_low = [s.lower() for s in doc.skills]
    m.skill_count = len(doc.skills)
    tech_pool = set(skills_low) | set(_WORD_RE.findall(blob))
    m.technologies = sorted({s for s in doc.skills})
    m.modern_tech = sorted({t for t in MODERN_TECH if t in tech_pool or t in blob})
    m.dated_tech = sorted({t for t in DATED_TECH if t in tech_pool or t in blob})
    m.cloud_exposure = any(t in blob for t in CLOUD_TECH)
    m.ai_exposure = any(t in blob for t in AI_TECH)
    m.production_exposure = any(t in blob for t in PRODUCTION_CUES)
    m.open_source = any(t in blob for t in OSS_CUES) or doc.links.get("github", False)
    low_endorsement = sum(1 for v in doc.skill_endorsements.values() if v < 2)
    m.tech_dumping = m.skill_count >= 25 and low_endorsement >= m.skill_count * 0.6

    # -- ATS keywords -------------------------------------------------------
    if jd:
        jd_terms = _keywords(jd)
        present = set(skills_low) | set(_WORD_RE.findall(blob))
        m.matched_keywords = sorted([t for t in jd_terms if t in present])[:25]
        m.missing_keywords = sorted([t for t in jd_terms if t not in present])[:25]
    counts: Dict[str, int] = {}
    for word in _WORD_RE.findall(blob):
        if len(word) > 3:
            counts[word] = counts.get(word, 0) + 1
    m.overused_keywords = sorted(
        [w for w, c in counts.items() if c >= 8 and w not in STRONG_ACTION_VERBS]
    )[:8]

    m.dimensions = _dimensions(doc, m)
    return m


def _keywords(text: str) -> List[str]:
    """Extract candidate ATS keywords from JD/resume text (deduped, meaningful)."""
    stop = {
        "and", "the", "for", "with", "you", "are", "our", "will", "have", "this",
        "that", "your", "who", "role", "team", "work", "years", "experience",
        "strong", "must", "plus", "job", "candidate", "ability", "including",
    }
    words = [w for w in _WORD_RE.findall(text.lower()) if len(w) > 3 and w not in stop]
    seen: List[str] = []
    for w in words:
        if w not in seen:
            seen.append(w)
    return seen[:40]


def _dimensions(doc: ResumeDocument, m: ResumeMetrics) -> Dict[str, float]:
    """Compute the resume-quality dimensions (0-100). Resume quality ONLY."""
    total_sections = 10.0
    present = len(doc.sections_present)
    structure = _clamp(50 + (present - 5) * 9)

    verb_ratio = (m.action_verb_bullets / m.bullet_count) if m.bullet_count else 0.0
    length_fit = 1.0 if 8 <= m.avg_bullet_words <= 28 else 0.5
    writing = _clamp(
        40 + verb_ratio * 45 + length_fit * 15 - len(m.buzzword_hits) * 6 - min(m.weak_verb_bullets, 6) * 2
    )

    tech_signals = sum(
        [m.cloud_exposure, m.ai_exposure, m.production_exposure, m.open_source]
    )
    technical_depth = _clamp(
        35 + len(m.modern_tech) * 5 + tech_signals * 8 - len(m.dated_tech) * 4
    )

    substantive_projects = [p for p in doc.projects if len(p.text.split()) >= 6]
    project_quality = _clamp(
        30 + len(substantive_projects) * 12 + (10 if m.production_exposure else 0)
    )

    achievements = _clamp(
        25 + len(m.quantified_statements) * 12 + len(m.recognition_statements) * 10
        + min(len(m.leadership_statements), 4) * 5
    )

    ats = _clamp(
        45 + present * 4
        + (len(m.matched_keywords) * 3 if m.matched_keywords else 0)
        - len(m.overused_keywords) * 3
        - (10 if m.tech_dumping else 0)
    )

    professionalism = _clamp(
        70 - len(m.buzzword_hits) * 8 - (10 if m.tech_dumping else 0)
        + (10 if doc.links.get("linkedin") else 0)
    )

    # Career narrative: seniority progression across roles + tenure sanity.
    career_narrative = _clamp(45 + _progression_bonus(doc))

    overall = _clamp(
        structure * 0.12
        + writing * 0.16
        + technical_depth * 0.16
        + project_quality * 0.14
        + achievements * 0.14
        + ats * 0.10
        + professionalism * 0.08
        + career_narrative * 0.10
    )

    return {
        "overall": overall,
        "structure": structure,
        "writing": writing,
        "technical_depth": technical_depth,
        "project_quality": project_quality,
        "achievements": achievements,
        "ats_friendliness": ats,
        "professionalism": professionalism,
        "career_narrative": career_narrative,
    }


_SENIORITY = ["intern", "junior", "associate", "engineer", "senior", "staff", "lead", "principal", "manager", "director", "vp", "head", "chief"]


def _seniority_rank(title: str) -> int:
    """Return a coarse seniority rank from a job title."""
    low = title.lower()
    rank = 0
    for i, level in enumerate(_SENIORITY):
        if level in low:
            rank = max(rank, i)
    return rank


def _progression_bonus(doc: ResumeDocument) -> float:
    """Return a career-progression bonus from title seniority over time."""
    if len(doc.experiences) < 2:
        return 5.0
    # Experiences are typically most-recent first; compare newest vs oldest.
    ranks = [_seniority_rank(e.title) for e in doc.experiences]
    newest, oldest = ranks[0], ranks[-1]
    if newest > oldest:
        return 30.0
    if newest == oldest:
        return 12.0
    return 0.0
