"""Report templates (Module 12).

All templates consume the **same** structured :class:`ExecutiveHiringReport` and
differ only in presentation: which sections appear, in what order, and the
audience framing on the cover. This is the Open/Closed heart of the report
system — adding an audience is a one-entry data change, never new rendering code.

A :class:`ReportTemplate` is pure configuration (no engine/UI import), so the
builder, renderer and exporters all share it without coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# Every section id the renderer knows how to build (see renderer.SECTION_BUILDERS).
_ALL_SECTIONS = [
    "executive_summary",
    "candidate_intelligence",
    "role_intelligence",
    "committee_decision",
    "risk_dashboard",
    "interview_strategy",
    "action_plan",
    "business_intelligence",
    "provenance",
]


@dataclass(frozen=True)
class ReportTemplate:
    """A named report layout for a specific audience.

    Attributes:
        key: Stable template key (used by the tool / copilot / UI).
        name: Human-readable template name.
        audience: Audience framing shown on the cover page.
        section_ids: Ordered section ids to include (subset of ``_ALL_SECTIONS``).
        summary: One-line description of the template's emphasis.
    """

    key: str
    name: str
    audience: str
    section_ids: List[str]
    summary: str = ""


TEMPLATES: Dict[str, ReportTemplate] = {
    "executive": ReportTemplate(
        key="executive",
        name="Executive Briefing",
        audience="Executive Leadership",
        section_ids=list(_ALL_SECTIONS),
        summary="The full boardroom briefing — every section.",
    ),
    "ceo": ReportTemplate(
        key="ceo",
        name="CEO Briefing",
        audience="Chief Executive Officer",
        section_ids=[
            "executive_summary",
            "business_intelligence",
            "committee_decision",
            "action_plan",
            "provenance",
        ],
        summary="Business impact and the decision — minimal technical detail.",
    ),
    "cto": ReportTemplate(
        key="cto",
        name="CTO Briefing",
        audience="Chief Technology Officer",
        section_ids=[
            "executive_summary",
            "candidate_intelligence",
            "role_intelligence",
            "committee_decision",
            "interview_strategy",
            "risk_dashboard",
            "provenance",
        ],
        summary="Technical depth, role fit and the interview strategy.",
    ),
    "hr": ReportTemplate(
        key="hr",
        name="HR Director Report",
        audience="HR / People Leadership",
        section_ids=[
            "executive_summary",
            "candidate_intelligence",
            "risk_dashboard",
            "committee_decision",
            "action_plan",
            "provenance",
        ],
        summary="Candidate profile, risk and onboarding plan.",
    ),
    "engineering_manager": ReportTemplate(
        key="engineering_manager",
        name="Engineering Manager Report",
        audience="Hiring Manager (Engineering)",
        section_ids=[
            "executive_summary",
            "candidate_intelligence",
            "role_intelligence",
            "interview_strategy",
            "risk_dashboard",
            "action_plan",
            "provenance",
        ],
        summary="Everything the hiring manager needs to run the loop.",
    ),
    "recruiter": ReportTemplate(
        key="recruiter",
        name="Recruiter Report",
        audience="Recruiting Team",
        section_ids=[
            "executive_summary",
            "candidate_intelligence",
            "interview_strategy",
            "action_plan",
            "provenance",
        ],
        summary="Actionable candidate brief and next steps.",
    ),
    "committee": ReportTemplate(
        key="committee",
        name="Hiring Committee Report",
        audience="Hiring Committee",
        section_ids=[
            "executive_summary",
            "committee_decision",
            "risk_dashboard",
            "provenance",
        ],
        summary="The committee's transparent deliberation and decision.",
    ),
}

# The default template used when none is specified.
DEFAULT_TEMPLATE = "executive"


def get_template(key: str) -> ReportTemplate:
    """Return the template for ``key`` (falls back to the default)."""
    return TEMPLATES.get((key or "").strip().lower(), TEMPLATES[DEFAULT_TEMPLATE])


def list_templates() -> List[ReportTemplate]:
    """Return every registered template (stable order)."""
    return list(TEMPLATES.values())
