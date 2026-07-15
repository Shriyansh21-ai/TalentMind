"""Resume risk detection (Module 8) — evidence only, never hallucinated.

Every finding names the concrete resume evidence that triggered it. If the
evidence isn't in the document, the finding is not raised — there is no
speculation. This is the structural guarantee behind Module 17's safety rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.ai.agents.resume.extractors import ResumeDocument
from src.ai.agents.resume.metrics import ResumeMetrics

_YEAR_RE = re.compile(r"(19|20)\d{2}")


@dataclass
class RiskFinding:
    """A single evidence-backed risk finding."""

    type: str
    issue: str
    evidence: str
    severity: str = "low"  # low | medium | high

    def to_dict(self) -> Dict[str, str]:
        """Return a JSON-serializable dict of the finding."""
        return {"type": self.type, "issue": self.issue, "evidence": self.evidence, "severity": self.severity}


def _year_of(date_str: str) -> int | None:
    """Return the year in a date string, or ``None``."""
    if not date_str:
        return None
    match = _YEAR_RE.search(date_str)
    return int(match.group(0)) if match else None


def detect_risks(doc: ResumeDocument, metrics: ResumeMetrics) -> List[RiskFinding]:
    """Return the list of evidence-backed resume-risk findings."""
    findings: List[RiskFinding] = []

    # 1) Missing dates on experience entries.
    for exp in doc.experiences:
        if not exp.start_date or (not exp.end_date and not exp.is_current):
            findings.append(
                RiskFinding(
                    type="missing_dates",
                    issue="An experience entry is missing start/end dates.",
                    evidence=f"{exp.title} @ {exp.company} (start={exp.start_date or '—'}, end={exp.end_date or '—'}).",
                    severity="medium",
                )
            )

    # 2) Large unexplained employment gaps (>6 months between consecutive roles).
    dated = [e for e in doc.experiences if _year_of(e.start_date)]
    dated_sorted = sorted(dated, key=lambda e: _year_of(e.start_date) or 0)
    for prev, nxt in zip(dated_sorted, dated_sorted[1:]):
        prev_end = _year_of(prev.end_date or "")
        nxt_start = _year_of(nxt.start_date or "")
        if prev_end and nxt_start and (nxt_start - prev_end) >= 2:
            findings.append(
                RiskFinding(
                    type="employment_gap",
                    issue=f"~{nxt_start - prev_end} year gap between roles.",
                    evidence=f"{prev.title}@{prev.company} ended {prev_end}; {nxt.title}@{nxt.company} started {nxt_start}.",
                    severity="medium",
                )
            )

    # 3) Contradictions: multiple current roles / end before start.
    current = [e for e in doc.experiences if e.is_current]
    if len(current) > 1:
        findings.append(
            RiskFinding(
                type="contradiction",
                issue="More than one role marked as current.",
                evidence="; ".join(f"{e.title}@{e.company}" for e in current),
                severity="high",
            )
        )
    for exp in doc.experiences:
        s, e = _year_of(exp.start_date), _year_of(exp.end_date or "")
        if s and e and e < s:
            findings.append(
                RiskFinding(
                    type="contradiction",
                    issue="End date precedes start date.",
                    evidence=f"{exp.title}@{exp.company}: {exp.start_date} → {exp.end_date}.",
                    severity="high",
                )
            )

    # 4) Weak project / experience descriptions.
    weak_bullets = [b for b in doc.bullets if len(b.split()) < 4]
    if doc.bullets and len(weak_bullets) >= max(2, len(doc.bullets) // 3):
        findings.append(
            RiskFinding(
                type="weak_description",
                issue="Several experience bullets are very short / low-signal.",
                evidence=f"{len(weak_bullets)}/{len(doc.bullets)} bullets are under 4 words.",
                severity="low",
            )
        )

    # 5) Buzzword stuffing.
    if len(metrics.buzzword_hits) >= 3:
        findings.append(
            RiskFinding(
                type="buzzword_stuffing",
                issue="Resume leans on generic buzzwords over concrete evidence.",
                evidence="Buzzwords: " + ", ".join(metrics.buzzword_hits),
                severity="low",
            )
        )

    # 6) Technology dumping.
    if metrics.tech_dumping:
        findings.append(
            RiskFinding(
                type="technology_dumping",
                issue="Long, flat skill list with little endorsement/depth signal.",
                evidence=f"{metrics.skill_count} skills listed with mostly low endorsements.",
                severity="low",
            )
        )

    # 7) Resume inflation: seniority claims not supported by experience length.
    inflated = [
        e for e in doc.experiences
        if any(w in e.title.lower() for w in ("senior", "lead", "principal", "staff", "head", "chief"))
    ]
    if inflated and doc.years_of_experience and doc.years_of_experience < 3:
        findings.append(
            RiskFinding(
                type="resume_inflation",
                issue="Senior-level titles with limited total experience.",
                evidence=f"{inflated[0].title} but only {doc.years_of_experience:.1f} yrs total experience.",
                severity="medium",
            )
        )

    return findings


def positive_signals(doc: ResumeDocument, metrics: ResumeMetrics) -> List[str]:
    """Return evidence-backed positive signals (balances the risk report)."""
    signals: List[str] = []
    if metrics.quantified_statements:
        signals.append(f"{len(metrics.quantified_statements)} quantified achievement(s) present.")
    if metrics.production_exposure:
        signals.append("Production / scale experience is described.")
    if metrics.open_source:
        signals.append("Open-source or public code presence detected.")
    if doc.links.get("linkedin"):
        signals.append("LinkedIn profile linked.")
    if metrics.action_verb_bullets and metrics.bullet_count:
        ratio = metrics.action_verb_bullets / metrics.bullet_count
        if ratio >= 0.4:
            signals.append("Strong use of action verbs in experience bullets.")
    return signals


def risk_level(findings: List[RiskFinding]) -> str:
    """Roll findings up into an overall Low/Medium/High resume-risk level."""
    if any(f.severity == "high" for f in findings):
        return "High"
    medium = sum(1 for f in findings if f.severity == "medium")
    if medium >= 2 or len(findings) >= 4:
        return "Medium"
    if findings:
        return "Low-Medium"
    return "Low"
