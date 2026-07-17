"""Tests for the Executive Hiring Report (Phase 4 / Milestone 4).

Covers the executive-report pipeline end-to-end — the schema (score-free), the
deterministic composer, the builder (which consumes existing committee/insight
outputs), the templates, the visualizations, the export engine (PDF/DOCX/HTML/
PPTX + named packets), automatic registration (AI platform + composer +
orchestration), safety/provenance and copilot delegation — all offline with
synthetic candidates (no dataset, no provider, no LLM).
"""

from __future__ import annotations

import io
import xml.dom.minidom as minidom
import zipfile

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.agents.executive_report import charts as charts_mod
from src.ai.agents.executive_report import validators
from src.ai.agents.executive_report.agent import (
    ExecutiveReportInput,
    build_executive_evidence,
)
from src.ai.agents.executive_report.builder import ExecutiveReportBuilder
from src.ai.agents.executive_report.composer import compose_executive_narrative
from src.ai.agents.executive_report.export import (
    FORMATS,
    PACKETS,
    export_packet,
    export_report,
)
from src.ai.agents.executive_report.schemas import (
    ExecutiveHiringReport,
    ExecutiveNarrative,
)
from src.ai.agents.executive_report.templates import get_template, list_templates
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard

JD = """Senior Machine Learning Engineer
What you'll do
- Design and own scalable ML systems in production
- Lead and mentor engineers
Requirements
- 8+ years experience
- Python, PyTorch, AWS, Kubernetes, LLMs
"""


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _report(template: str = "executive", jd: str = JD, **kw) -> ExecutiveHiringReport:
    builder = ExecutiveReportBuilder(ai_runner=_runner())
    return builder.build(
        candidate=make_candidate(candidate_id=kw.pop("candidate_id", "CAND_1")),
        jd=jd,
        template=template,
        generated_on="2026-07-15",
        **kw,
    )


# ---------------------------------------------------------------------------
# Registration + schema (final requirements, Modules 14/16)
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("executive_hiring_report")


def test_composer_registered():
    assert has_composer(ExecutiveNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("executive_report")
    assert any(a.descriptor.name == "executive_hiring_report" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(ExecutiveNarrative)


def test_narrative_top_level_has_no_score_fields():
    for name in ExecutiveNarrative.field_names():
        assert not any(tok in name.lower() for tok in ("score", "rating", "percent"))


# ---------------------------------------------------------------------------
# Composer (offline reasoning) — restates, never invents
# ---------------------------------------------------------------------------


def test_composer_uses_committee_recommendation_when_present():
    evidence = {
        "candidate_overview": {
            "title": "Senior ML Engineer",
            "company": "Acme",
            "years_of_experience": 9,
        },
        "committee": {
            "consensus": {"recommendation": "Hire"},
            "confidence": {"overall": 80.0},
            "decision": {
                "executive_summary": "Strong candidate.",
                "business_justification": "Ships value.",
            },
        },
        "recommendation": {"recommendation": "Lean Hire", "reasons": ["x"]},
    }
    out = compose_executive_narrative(evidence)
    assert out["overall_recommendation"] == "Hire"
    assert out["executive_confidence"] == "High"
    assert "AI Hiring Committee" in out["business_impact"]


def test_composer_falls_back_to_recommendation_engine():
    evidence = {"recommendation": {"recommendation": "Strong Fit", "reasons": ["deep expertise"]}}
    out = compose_executive_narrative(evidence)
    assert out["overall_recommendation"] == "Strong Fit"
    assert out["executive_summary"]


def test_composer_never_empty_summary():
    out = compose_executive_narrative({})
    assert out["executive_summary"].strip()
    # Composer output must validate against the schema.
    ExecutiveNarrative(**out)


def test_build_evidence_packs_all_sources():
    payload = ExecutiveReportInput(candidate_id="C1", intelligence={"overall_score": 80})
    evidence = build_executive_evidence(payload)
    for key in (
        "committee",
        "resume",
        "jd",
        "intelligence",
        "timeline",
        "risk",
        "recommendation",
        "interview",
    ):
        assert key in evidence


# ---------------------------------------------------------------------------
# Builder — consumes existing intelligence, assembles a unified report
# ---------------------------------------------------------------------------


def test_builder_produces_unified_report():
    report = _report()
    assert isinstance(report, ExecutiveHiringReport)
    assert report.narrative.executive_summary
    assert report.narrative.overall_recommendation
    assert report.action_plan.primary_action
    # All eight business-intelligence estimates carry a confidence (Module 9).
    for _name, est in report.business_intelligence.items():
        assert 0 <= est.confidence <= 100
        assert est.level in ("High", "Moderate", "Low")


def test_builder_integrates_committee():
    report = _report()
    assert report.committee  # committee decision is present
    assert report.committee.get("consensus", {}).get("recommendation")
    assert "AI Hiring Committee" in report.evidence_sources


def test_builder_consumes_many_sources():
    report = _report()
    # Resume, JD, intelligence, timeline, risk, recommendation, interview, committee.
    assert len(report.evidence_sources) >= 6


def test_builder_is_deterministic():
    r1 = _report(candidate_id="CAND_DET")
    r2 = _report(candidate_id="CAND_DET")
    assert r1.narrative.overall_recommendation == r2.narrative.overall_recommendation
    assert r1.action_plan.primary_action == r2.action_plan.primary_action


def test_builder_degrades_without_jd():
    report = _report(jd="")
    assert report.narrative.executive_summary
    assert any("JD" in w for w in report.warnings)


def test_builder_without_committee():
    builder = ExecutiveReportBuilder(ai_runner=_runner())
    report = builder.build(
        candidate=make_candidate(), jd=JD, run_committee=False, generated_on="2026-07-15"
    )
    assert not report.committee
    assert report.narrative.executive_summary


def test_report_to_dict_is_serializable():
    import json

    assert json.dumps(_report().to_dict())


# ---------------------------------------------------------------------------
# Safety / provenance (Module 16)
# ---------------------------------------------------------------------------


def test_provenance_every_statement_attributed():
    report = _report()
    assert report.provenance
    for entry in report.provenance:
        assert entry.source
        assert entry.kind in validators.ALLOWED_KINDS
        assert entry.statement
    # No provenance warnings for a full-evidence report.
    assert validators.validate_provenance(report.provenance) == []


def test_provenance_separates_registers():
    report = _report()
    kinds = {p.kind for p in report.provenance}
    assert "Recommendation" in kinds
    assert kinds <= set(validators.ALLOWED_KINDS)


# ---------------------------------------------------------------------------
# Templates (Module 12) — same data, different presentation
# ---------------------------------------------------------------------------


def test_all_templates_build_and_differ():
    keys = [t.key for t in list_templates()]
    assert {
        "executive",
        "ceo",
        "cto",
        "hr",
        "engineering_manager",
        "recruiter",
        "committee",
    } <= set(keys)
    exec_sections = get_template("executive").section_ids
    ceo_sections = get_template("ceo").section_ids
    assert exec_sections != ceo_sections  # different presentation
    for key in keys:
        html = export_report(_report(template=key), "html", key)
        assert html and b"<!doctype html" in html.lower()


def test_get_template_falls_back_to_default():
    assert get_template("nonexistent").key == "executive"


# ---------------------------------------------------------------------------
# Visualizations (Module 10)
# ---------------------------------------------------------------------------


def test_chart_data_built_for_every_visual():
    report = _report()
    for key in (
        "scorecard",
        "radar",
        "risk_matrix",
        "consensus_meter",
        "confidence_distribution",
        "career_growth",
        "skill_distribution",
        "interview_roadmap",
    ):
        assert key in report.charts


def test_chart_data_is_pure_and_bounded():
    charts = charts_mod.build_chart_data(
        intelligence={"overall_score": 82, "technical_score": 90},
        timeline={"timeline_score": 70},
        risk={"job_hopping_risk": "High", "leadership_risk": "Low"},
        committee={"consensus": {"weighted_stance": 1.5}, "confidence": {"evidence_coverage": 88}},
        interview={"technical_topics": ["a", "b"]},
        resume={"quality": {"overall": 80, "writing": 75}},
    )
    assert charts["scorecard"]["Overall"] == 82
    assert 0.0 <= charts["consensus_meter"] <= 1.0
    assert charts["risk_matrix"]["Job Hopping"] > charts["risk_matrix"]["Leadership"]
    assert charts["interview_roadmap"]["Technical"] == 2


# ---------------------------------------------------------------------------
# Export engine (Module 11) — valid bytes for every format + packet
# ---------------------------------------------------------------------------


def test_all_formats_export_valid_bytes():
    report = _report()
    outputs = {fmt: export_report(report, fmt, "executive") for fmt in FORMATS}
    assert outputs["pdf"][:5] == b"%PDF-" and b"%%EOF" in outputs["pdf"][-16:]
    assert outputs["html"][:15].lower().startswith(b"<!doctype html")
    for fmt in ("docx", "pptx"):
        data = outputs[fmt]
        assert data[:2] == b"PK"
        zf = zipfile.ZipFile(io.BytesIO(data))
        assert zf.testzip() is None  # every member CRC is valid


def test_ooxml_parts_are_well_formed_xml():
    report = _report(candidate_id="CAND_&<>1")  # force escaping
    for fmt in ("docx", "pptx"):
        zf = zipfile.ZipFile(io.BytesIO(export_report(report, fmt, "executive")))
        for name in zf.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                minidom.parseString(zf.read(name))  # raises on malformed XML


def test_docx_and_pptx_contain_required_parts():
    report = _report()
    docx_zip = zipfile.ZipFile(io.BytesIO(export_report(report, "docx", "executive")))
    assert "word/document.xml" in docx_zip.namelist()
    pptx_zip = zipfile.ZipFile(io.BytesIO(export_report(report, "pptx", "executive")))
    names = pptx_zip.namelist()
    assert "ppt/presentation.xml" in names
    assert any(n.startswith("ppt/slides/slide") for n in names)


def test_named_packets_export():
    report = _report()
    for key in PACKETS:
        data, mime, filename = export_packet(report, key)
        assert data and mime and filename.startswith(report.candidate_id)


def test_export_rejects_unknown_format():
    import pytest

    with pytest.raises(ValueError):
        export_report(_report(), "xls", "executive")


# ---------------------------------------------------------------------------
# Copilot integration (Module 14)
# ---------------------------------------------------------------------------


def test_copilot_routes_executive_report_questions():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "Generate executive report",
        "Generate CTO report",
        "Generate recruiter report",
        "Export committee report",
        "Create interview packet",
        "Generate the board briefing as pptx",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.EXECUTIVE_REPORT


def test_copilot_executive_intent_selects_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.EXECUTIVE_REPORT) == ["executive_report"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Analyze this candidate in detail": Intent.ANALYZE_CANDIDATE,
        "Find machine learning engineers": Intent.SEARCH_CANDIDATE,
        "Review this resume": Intent.RESUME_REVIEW,
        "Analyze this JD": Intent.JD_ANALYSIS,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
        "What did the committee disagree on?": Intent.HIRING_COMMITTEE,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_executive_report_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(
        [make_candidate(candidate_id="CAND_0000001", title="Senior ML Engineer")]
    )
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "Generate CTO report for CAND_0000001 as pptx", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.EXECUTIVE_REPORT
    assert "executive_report" in [t["name"] for t in turn.tools_used]
    assert "Executive Hiring Report" in turn.evidence_sources
    assert turn.answer


def test_tool_routes_template_and_format():
    from src.ai.tools.executive_report_tools import route_request

    assert route_request("generate a CTO report as pptx")["template"] == "cto"
    assert route_request("generate a CTO report as pptx")["format"] == "pptx"
    assert route_request("export committee report")["packet"] == "committee_report"
