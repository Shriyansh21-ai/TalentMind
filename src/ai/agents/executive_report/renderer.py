"""Report document IR + builder (the single presentation model).

Every exporter (PDF, DOCX, HTML, PPTX) and the Streamlit dashboard render the
**same** intermediate representation, so the report looks identical everywhere
and there is one place that decides what a section contains. This is the DRY core
of the rendering system: engines produce data → the builder assembles an
:class:`ExecutiveHiringReport` → this module flattens it into a
:class:`ReportDocument` → each renderer walks the document.

A :class:`ReportDocument` is a cover + a table of contents + an ordered list of
:class:`Section`, each a list of typed :class:`Block` s. The set and order of
sections is chosen by the report template (Module 12), so the same data renders
as an Executive, CTO, HR, Recruiter, CEO, Engineering-Manager or Committee brief.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.ai.agents.executive_report.branding import DEFAULT_BRAND, Brand, section_number
from src.ai.agents.executive_report.schemas import ExecutiveHiringReport


# ---------------------------------------------------------------------------
# Intermediate representation
# ---------------------------------------------------------------------------


@dataclass
class Block:
    """One renderable unit inside a section.

    ``kind`` is one of: ``paragraph``, ``subheading``, ``bullets``, ``kv``
    (key/value rows), ``metric`` (a labelled 0-100 bar), ``note`` (caption).
    """

    kind: str
    text: str = ""
    items: List[str] = field(default_factory=list)
    rows: List[Tuple[str, str]] = field(default_factory=list)
    metrics: List[Tuple[str, float, str]] = field(default_factory=list)


@dataclass
class Section:
    """A numbered report section (Module 13)."""

    number: str
    title: str
    blocks: List[Block] = field(default_factory=list)


@dataclass
class ReportDocument:
    """The full, render-agnostic executive document."""

    title: str
    subtitle: str
    cover: Dict[str, Any]
    sections: List[Section]
    brand: Brand = DEFAULT_BRAND
    footer: str = ""

    @property
    def toc(self) -> List[Tuple[str, str]]:
        """Return the table of contents as ``(number, title)`` pairs."""
        return [(s.number, s.title) for s in self.sections]


# ---------------------------------------------------------------------------
# Section builders (one per report section; each reads the report verbatim)
# ---------------------------------------------------------------------------


def _s_executive_summary(report: ExecutiveHiringReport) -> List[Block]:
    n = report.narrative
    return [
        Block("paragraph", text=n.executive_summary),
        Block(
            "kv",
            rows=[
                ("Overall Recommendation", n.overall_recommendation),
                ("Executive Confidence", n.executive_confidence),
            ],
        ),
        Block("subheading", text="Business Impact"),
        Block("paragraph", text=n.business_impact),
        Block("subheading", text="Technical Impact"),
        Block("paragraph", text=n.technical_impact),
        Block("subheading", text="Leadership Potential"),
        Block("paragraph", text=n.leadership_potential),
        Block("subheading", text="Risk Overview"),
        Block("paragraph", text=n.risk_overview),
        Block("subheading", text="Interview Readiness"),
        Block("paragraph", text=n.interview_readiness),
        Block("subheading", text="Top Reasons"),
        Block("bullets", items=n.top_reasons or ["Not substantiated in the evidence."]),
        Block("subheading", text="Top Concerns"),
        Block("bullets", items=n.top_concerns or ["None surfaced by the evidence."]),
        Block("note", text=n.confidence_note),
    ]


def _s_candidate_intelligence(report: ExecutiveHiringReport) -> List[Block]:
    ci = report.candidate_intelligence or {}
    tl = report.role_intelligence.get("_timeline", {}) if report.role_intelligence else {}
    blocks = [
        Block(
            "metric",
            metrics=[
                ("Overall", float(ci.get("overall_score", 0.0)), "Candidate Intelligence"),
                ("Technical", float(ci.get("technical_score", 0.0)), ""),
                ("Leadership", float(ci.get("leadership_score", 0.0)), ""),
                ("Career Growth", float(ci.get("career_growth_score", 0.0)), ""),
                ("Learning Velocity", float(ci.get("learning_velocity", 0.0)), ""),
            ],
        ),
    ]
    story = (report.candidate_overview or {}).get("career_story") or tl.get("career_story")
    if story:
        blocks += [Block("subheading", text="Career Trajectory"), Block("paragraph", text=story)]
    if ci.get("strengths"):
        blocks += [Block("subheading", text="Achievements & Strengths"), Block("bullets", items=list(ci["strengths"])[:6])]
    if ci.get("weaknesses"):
        blocks += [Block("subheading", text="Development Areas"), Block("bullets", items=list(ci["weaknesses"])[:6])]
    rq = report.role_intelligence.get("_resume_quality") if report.role_intelligence else None
    if isinstance(rq, dict) and rq:
        blocks.append(
            Block("note", text=f"Resume quality (not a hiring score): overall {rq.get('overall', 0):.0f}/100.")
        )
    return blocks


def _s_role_intelligence(report: ExecutiveHiringReport) -> List[Block]:
    ri = report.role_intelligence or {}
    blocks = [Block("paragraph", text=report.jd_summary or "No job description was analysed for this report.")]
    rows = []
    for label, key in [
        ("Seniority", "seniority"),
        ("Technical Level", "technical_level"),
        ("Primary Hiring Intent", "primary_intent"),
        ("Organization Maturity", "organization_maturity"),
        ("Market Competitiveness", "market_competitiveness"),
        ("Role Clarity", "role_clarity"),
    ]:
        if ri.get(key):
            rows.append((label, str(ri[key])))
    if rows:
        blocks.append(Block("kv", rows=rows))
    if ri.get("mandatory"):
        blocks += [Block("subheading", text="Requirement Hierarchy — Mandatory"), Block("bullets", items=list(ri["mandatory"])[:6])]
    if ri.get("technology_stack"):
        blocks += [Block("subheading", text="Technology Stack"), Block("bullets", items=list(ri["technology_stack"])[:8])]
    if ri.get("business_priorities"):
        blocks += [Block("subheading", text="Business Priorities"), Block("bullets", items=list(ri["business_priorities"])[:5])]
    return blocks


def _s_committee(report: ExecutiveHiringReport) -> List[Block]:
    committee = report.committee or {}
    if not committee:
        return [Block("paragraph", text="The AI Hiring Committee was not convened for this report.")]
    consensus = committee.get("consensus", {})
    decision = committee.get("decision", {})
    confidence = committee.get("confidence", {})
    blocks = [
        Block(
            "kv",
            rows=[
                ("Committee Recommendation", str(consensus.get("recommendation", "n/a"))),
                ("Consensus", str(consensus.get("level", "n/a"))),
                ("Overall Confidence", f"{confidence.get('overall', 0):.0f}/100"),
                ("Conflicts", str(len(committee.get("conflicts", [])))),
            ],
        ),
        Block("subheading", text="Committee Chair Summary"),
        Block("paragraph", text=decision.get("executive_summary", "")),
    ]
    opinions = committee.get("opinions", [])
    if opinions:
        blocks.append(Block("subheading", text="Every Committee Opinion"))
        blocks.append(
            Block(
                "bullets",
                items=[
                    f"{o.get('role_title', o.get('role', 'Member'))}: "
                    f"{o.get('recommendation')} (confidence {o.get('confidence', 0):.0f}%)"
                    for o in opinions
                ],
            )
        )
    disagreements = committee.get("discussion", {}).get("disagreements", [])
    if disagreements:
        blocks += [Block("subheading", text="Disagreements"), Block("bullets", items=list(disagreements)[:5])]
    conflicts = committee.get("conflicts", [])
    if conflicts:
        blocks.append(Block("subheading", text="Conflict Resolution"))
        blocks.append(
            Block(
                "bullets",
                items=[
                    f"{c.get('member_a')} vs {c.get('member_b')} → {c.get('resolution_strategy', '')}"
                    for c in conflicts[:5]
                ],
            )
        )
    return blocks


def _s_risk(report: ExecutiveHiringReport) -> List[Block]:
    rd = report.risk_dashboard or {}
    blocks = [
        Block(
            "kv",
            rows=[
                ("Overall Risk", str(rd.get("risk_level", "Unknown"))),
                ("Risk Score", f"{rd.get('risk_score', 0):.0f}/100"),
                ("Career Consistency", f"{rd.get('career_consistency', 0):.0f}/100"),
            ],
        ),
    ]
    sub = [
        ("Employment Gap", rd.get("employment_gap_risk")),
        ("Job Hopping", rd.get("job_hopping_risk")),
        ("Skill Stagnation", rd.get("skill_stagnation_risk")),
        ("Technical Depth", rd.get("technical_depth_risk")),
        ("Leadership", rd.get("leadership_risk")),
        ("Communication", rd.get("communication_risk")),
    ]
    rows = [(label, str(value)) for label, value in sub if value]
    if rows:
        blocks += [Block("subheading", text="Risk Matrix (sub-risks)"), Block("kv", rows=rows)]
    if rd.get("red_flags"):
        blocks += [Block("subheading", text="Red Flags"), Block("bullets", items=list(rd["red_flags"])[:6])]
    if rd.get("validation_questions"):
        blocks += [Block("subheading", text="Mitigations — Validate in Interview"), Block("bullets", items=list(rd["validation_questions"])[:6])]
    if rd.get("positive_signals"):
        blocks += [Block("subheading", text="Mitigating Signals"), Block("bullets", items=list(rd["positive_signals"])[:5])]
    return blocks


def _s_interview(report: ExecutiveHiringReport) -> List[Block]:
    iv = report.interview_strategy
    blocks = []
    if iv.roadmap:
        blocks += [Block("subheading", text="Interview Roadmap"), Block("bullets", items=iv.roadmap)]
    for title, items in [
        ("Technical Interview", iv.technical_interview),
        ("System Design", iv.system_design),
        ("Behavioral Interview", iv.behavioral_interview),
        ("Leadership Interview", iv.leadership_interview),
        ("Coding Interview", iv.coding_interview),
        ("Evaluation Rubric", iv.evaluation_rubric),
        ("Decision Checkpoints", iv.decision_checkpoints),
    ]:
        if items:
            blocks += [Block("subheading", text=title), Block("bullets", items=items)]
    if iv.post_interview_recommendation:
        blocks += [Block("subheading", text="Post-Interview Recommendation"), Block("paragraph", text=iv.post_interview_recommendation)]
    return blocks


def _s_action_plan(report: ExecutiveHiringReport) -> List[Block]:
    ap = report.action_plan
    blocks = [
        Block("kv", rows=[("Recommended Action", ap.primary_action)]),
        Block("paragraph", text=ap.rationale),
    ]
    if ap.alternatives:
        blocks += [Block("subheading", text="Alternative Dispositions"), Block("bullets", items=ap.alternatives)]
    if ap.onboarding_plan:
        blocks += [Block("subheading", text="Expected Onboarding Plan"), Block("bullets", items=ap.onboarding_plan)]
    for title, items in [
        ("First 30 Days", ap.plan_30_day),
        ("First 60 Days", ap.plan_60_day),
        ("First 90 Days", ap.plan_90_day),
    ]:
        if items:
            blocks += [Block("subheading", text=title), Block("bullets", items=items)]
    return blocks


def _s_business_intelligence(report: ExecutiveHiringReport) -> List[Block]:
    bi = report.business_intelligence
    blocks: List[Block] = []
    for name, est in bi.items():
        blocks.append(
            Block(
                "kv",
                rows=[
                    (name, f"{est.level} — confidence {est.confidence:.0f}%"),
                ],
            )
        )
        if est.rationale:
            blocks.append(Block("note", text=est.rationale))
    return blocks


def _s_provenance(report: ExecutiveHiringReport) -> List[Block]:
    blocks = [
        Block(
            "paragraph",
            text=(
                "Every statement in this report is traceable to a TalentMind engine "
                "or agent. Evidence, Inference and Recommendation are kept distinct."
            ),
        ),
        Block("kv", rows=[(p.kind, f"{p.statement}  —  [{p.source}]") for p in report.provenance]),
    ]
    if report.evidence_sources:
        blocks.append(Block("subheading", text="Evidence Sources"))
        blocks.append(Block("bullets", items=list(report.evidence_sources)))
    if report.warnings:
        blocks.append(Block("subheading", text="Caveats"))
        blocks.append(Block("bullets", items=list(report.warnings)))
    return blocks


# Registry of section-id → (title, builder). The template selects and orders ids.
SECTION_BUILDERS: Dict[str, Tuple[str, Any]] = {
    "executive_summary": ("Executive Summary", _s_executive_summary),
    "candidate_intelligence": ("Candidate Intelligence", _s_candidate_intelligence),
    "role_intelligence": ("Role Intelligence", _s_role_intelligence),
    "committee_decision": ("Committee Decision", _s_committee),
    "risk_dashboard": ("Risk Dashboard", _s_risk),
    "interview_strategy": ("Interview Strategy", _s_interview),
    "action_plan": ("Executive Action Plan", _s_action_plan),
    "business_intelligence": ("Business Intelligence", _s_business_intelligence),
    "provenance": ("Evidence & Provenance", _s_provenance),
}


def build_document(
    report: ExecutiveHiringReport,
    section_ids: Optional[List[str]] = None,
    *,
    brand: Brand = DEFAULT_BRAND,
    audience: str = "Executive Leadership",
) -> ReportDocument:
    """Flatten a report into a :class:`ReportDocument` for the given sections."""
    ids = section_ids or list(SECTION_BUILDERS.keys())
    sections: List[Section] = []
    for index, sid in enumerate(ids, start=1):
        entry = SECTION_BUILDERS.get(sid)
        if entry is None:
            continue
        title, builder = entry
        sections.append(Section(number=section_number(index), title=title, blocks=builder(report)))

    ov = report.candidate_overview or {}
    cover = {
        "candidate_id": report.candidate_id,
        "title": ov.get("title", ""),
        "company": ov.get("company", ""),
        "recommendation": report.narrative.overall_recommendation,
        "confidence": report.narrative.executive_confidence,
        "generated_on": report.generated_on,
        "audience": audience,
        "logo": brand.logo_placeholder,
    }
    return ReportDocument(
        title=f"{brand.product} Executive Hiring Report",
        subtitle=f"{ov.get('title', 'Candidate')} · {report.candidate_id}",
        cover=cover,
        sections=sections,
        brand=brand,
        footer=f"{brand.product} — {brand.tagline}. Confidential.",
    )
