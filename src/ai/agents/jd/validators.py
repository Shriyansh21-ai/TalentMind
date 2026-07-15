"""JD hiring-risk detection (Module 8) — evidence only, never hallucinated.

Every finding names the concrete JD evidence that triggered it. If the evidence
isn't in the JD, the finding is not raised — no speculation (Module 17).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

from src.ai.agents.jd.extractors import JDDocument
from src.ai.agents.jd.metrics import JDMetrics

_JUNIOR_TITLE = ("intern", "junior", "entry", "graduate", "associate", "trainee")
_SENIOR_TITLE = ("senior", "staff", "principal", "lead", "director", "head", "architect")
_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*(?:years|yrs|yr)")


@dataclass
class RiskFinding:
    """A single evidence-backed JD-risk finding."""

    type: str
    issue: str
    evidence: str
    severity: str = "low"  # low | medium | high

    def to_dict(self) -> Dict[str, str]:
        """Return a JSON-serializable dict of the finding."""
        return {"type": self.type, "issue": self.issue, "evidence": self.evidence, "severity": self.severity}


def detect_risks(doc: JDDocument, metrics: JDMetrics) -> List[RiskFinding]:
    """Return the list of evidence-backed JD hiring-risk findings."""
    findings: List[RiskFinding] = []
    blob = doc.all_text()
    title_low = doc.title.lower()
    years = doc.years_experience or 0

    # 1) Conflicting seniority vs experience (junior title, senior experience).
    if any(t in title_low for t in _JUNIOR_TITLE) and years >= 6:
        findings.append(
            RiskFinding(
                type="conflicting_requirements",
                issue="Junior-level title but senior years of experience required.",
                evidence=f"Title '{doc.title}' with {years}+ years required.",
                severity="high",
            )
        )
    if any(t in title_low for t in _SENIOR_TITLE) and 0 < years <= 1:
        findings.append(
            RiskFinding(
                type="conflicting_requirements",
                issue="Senior-level title but very low experience requirement.",
                evidence=f"Title '{doc.title}' with only {years} year(s) required.",
                severity="medium",
            )
        )

    # 2) Unrealistic experience expectations.
    if years >= 15:
        findings.append(
            RiskFinding(
                type="unrealistic_expectations",
                issue="Very high years-of-experience requirement may shrink the funnel.",
                evidence=f"{years}+ years required.",
                severity="medium",
            )
        )
    # Unrealistic per-tech experience for a young technology (e.g. "10 years of Rust").
    for tech in metrics.modern_tech:
        pat = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)[^.]{0,30}\b" + re.escape(tech), blob)
        if pat and int(pat.group(1)) >= 8:
            findings.append(
                RiskFinding(
                    type="unrealistic_expectations",
                    issue=f"Improbable experience length demanded for a relatively new technology ({tech}).",
                    evidence=pat.group(0),
                    severity="medium",
                )
            )

    # 3) Too many technologies (technology overload).
    if metrics.tech_count >= 15:
        findings.append(
            RiskFinding(
                type="too_many_technologies",
                issue="Very broad technology list; risks an unfillable 'unicorn' role.",
                evidence=f"{metrics.tech_count} distinct technologies referenced.",
                severity="medium",
            )
        )

    # 4) Missing compensation.
    if not doc.compensation:
        findings.append(
            RiskFinding(
                type="missing_compensation",
                issue="No compensation information provided.",
                evidence="No salary/compensation section detected in the JD.",
                severity="low",
            )
        )

    # 5) Poor role definition / missing responsibilities.
    if not doc.responsibilities:
        findings.append(
            RiskFinding(
                type="missing_responsibilities",
                issue="No responsibilities / 'what you'll do' section detected.",
                evidence="Responsibilities section absent.",
                severity="medium",
            )
        )

    # 6) Missing evaluation criteria / requirements.
    if not doc.requirements:
        findings.append(
            RiskFinding(
                type="missing_evaluation_criteria",
                issue="No explicit requirements / qualifications to evaluate against.",
                evidence="Requirements section absent.",
                severity="high",
            )
        )

    # 7) Hiring-bias indicators.
    if metrics.bias_terms:
        findings.append(
            RiskFinding(
                type="hiring_bias",
                issue="Potentially biased or exclusionary language detected.",
                evidence="Terms: " + ", ".join(metrics.bias_terms),
                severity="medium",
            )
        )

    # 8) Ambiguity / vagueness.
    if len(metrics.vague_terms) >= 2:
        findings.append(
            RiskFinding(
                type="ambiguity",
                issue="Vague filler language reduces role clarity.",
                evidence="Terms: " + ", ".join(metrics.vague_terms),
                severity="low",
            )
        )

    return findings


def positive_signals(doc: JDDocument, metrics: JDMetrics) -> List[str]:
    """Return evidence-backed positive signals (balances the risk report)."""
    signals: List[str] = []
    if doc.compensation:
        signals.append("Compensation is disclosed.")
    if doc.responsibilities and doc.requirements:
        signals.append("Both responsibilities and requirements are present.")
    if doc.preferred:
        signals.append("Requirements are split into mandatory vs preferred.")
    if doc.benefits:
        signals.append("Benefits are described.")
    if metrics.modern_tech and not metrics.dated_tech:
        signals.append("Modern technology stack with no legacy tech.")
    return signals


def risk_level(findings: List[RiskFinding]) -> str:
    """Roll findings up into an overall Low/Medium/High JD-risk level."""
    if any(f.severity == "high" for f in findings):
        return "High"
    medium = sum(1 for f in findings if f.severity == "medium")
    if medium >= 2 or len(findings) >= 4:
        return "Medium"
    if findings:
        return "Low-Medium"
    return "Low"
