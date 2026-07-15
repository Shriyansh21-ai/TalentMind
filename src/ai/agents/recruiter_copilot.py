"""RecruiterCopilotAgent — narrates structured tool outputs into recruiter prose.

This is the AI-Platform agent behind the Recruiter Copilot. It receives ONLY the
structured outputs of deterministic tools (never raw resumes or raw JSON dumps)
and produces a :class:`CopilotResponse`. Offline it uses a deterministic composer
(no hallucination, cannot contradict the engines); with a real provider it uses
the same evidence embedded in the prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.providers.composers import register_composer
from src.ai.schemas.copilot_response import CopilotResponse

# Map tool name -> the engine label to cite as evidence.
_TOOL_EVIDENCE = {
    "faiss_search": "FAISS semantic search",
    "candidate_search": "Candidate search",
    "skill_gap": "Skill-gap analyzer",
    "candidate_intelligence": "Candidate Intelligence engine",
    "timeline": "Career Timeline Intelligence",
    "risk": "Resume Risk Detection",
    "recommendation": "Hiring Recommendation engine",
    "interview": "Interview Intelligence",
    "explainability": "Rule-based explainability",
    "comparison": "Candidate Comparison engine",
    "pipeline": "Hiring Pipeline",
    "dashboard": "Recruiter Dashboard analytics",
    "resume_analysis": "Resume Analyst Agent",
    "jd_analysis": "JD Analyst Agent",
    "hiring_committee": "AI Hiring Committee",
    "executive_report": "Executive Hiring Report",
    "interview_studio": "Interview Studio",
    "compensation_governance": "Compensation Governance",
    "pay_equity_guardian": "Pay Equity Guardian",
    "hiring_compliance": "Hiring Compliance",
    "hiring_audit": "Hiring Audit",
    "hiring_intelligence": "Hiring Intelligence",
}


@dataclass
class RecruiterCopilotInput:
    """Typed input for the RecruiterCopilotAgent.

    Attributes:
        intent: The detected intent value (string).
        message: The recruiter's message.
        tool_outputs: ``{tool_name: output_dict}`` for the tools that ran.
    """

    intent: str
    message: str
    tool_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)


def build_evidence(payload: RecruiterCopilotInput) -> Dict[str, Any]:
    """Return the structured evidence for the agent/composer."""
    return {
        "intent": payload.intent,
        "message": payload.message,
        "tools": payload.tool_outputs,
    }


# ---------------------------------------------------------------------------
# Deterministic composer (offline reasoning)
# ---------------------------------------------------------------------------


def _summarize_search(output: Dict[str, Any]) -> str:
    rows = output.get("results", [])
    if not rows:
        return "No candidates matched the query."
    lines = [
        f"{i}. {r.get('title', 'Candidate')} @ {r.get('company', '?')} "
        f"({r.get('candidate_id')}) — {r.get('years_of_experience', '?')} yrs"
        for i, r in enumerate(rows[:5], start=1)
    ]
    return "Top matches:\n" + "\n".join(lines)


def _summarize_intelligence(output: Dict[str, Any]) -> str:
    return (
        f"Intelligence: overall {output.get('overall', 0):.0f}/100, technical "
        f"{output.get('technical', 0):.0f}, leadership {output.get('leadership', 0):.0f}, "
        f"engine recommendation '{output.get('recommendation', 'n/a')}'."
    )


def _summarize_timeline(output: Dict[str, Any]) -> str:
    return (
        f"Career: {output.get('summary', 'trajectory analysed')} "
        f"(timeline {output.get('timeline_score', 0):.0f}/100, "
        f"{output.get('promotion_count', 0)} promotion(s))."
    )


def _summarize_risk(output: Dict[str, Any]) -> str:
    flags = output.get("red_flags", [])
    tail = f" Red flags: {', '.join(flags)}." if flags else " No red flags."
    return (
        f"Risk: {output.get('risk_level', 'Unknown')} "
        f"(score {output.get('risk_score', 0):.0f}/100).{tail}"
    )


def _summarize_recommendation(output: Dict[str, Any]) -> str:
    reasons = output.get("reasons", [])
    tail = f" Reasons: {'; '.join(reasons)}." if reasons else ""
    return (
        f"Recommendation: {output.get('recommendation', 'n/a')} "
        f"({output.get('confidence', 0):.0f}% confidence).{tail}"
    )


def _summarize_interview(output: Dict[str, Any]) -> str:
    topics = output.get("technical_topics", []) + output.get("system_design_topics", [])
    return "Interview focus: " + ("; ".join(topics[:5]) if topics else "standard rounds") + "."


def _summarize_skill_gap(output: Dict[str, Any]) -> str:
    missing = output.get("missing", [])
    tail = f" Missing: {', '.join(missing)}." if missing else " No JD skill gaps."
    return f"Skill match: {output.get('match_percent', 0)}%.{tail}"


def _summarize_comparison(output: Dict[str, Any]) -> str:
    rows = output.get("rows", [])
    best = output.get("best_by_metric", {})
    if not rows:
        return "No comparison data."
    leader = best.get("overall_score")
    lines = [
        f"- {r.get('title')} ({r.get('candidate_id')}): overall "
        f"{r.get('overall_score', 0):.0f}, technical {r.get('technical_score', 0):.0f}, "
        f"risk {r.get('risk_level')}"
        for r in rows
    ]
    tail = f" Strongest overall: {leader}." if leader else ""
    return "Comparison:\n" + "\n".join(lines) + tail


def _summarize_pipeline(output: Dict[str, Any]) -> str:
    if output.get("tracked") is False:
        return "Pipeline: candidate is not yet tracked."
    if "current_stage" in output:
        return (
            f"Pipeline: at '{output.get('current_stage')}' "
            f"({output.get('status')}), priority {output.get('priority')}."
        )
    dist = output.get("stage_distribution", {})
    active = {k: v for k, v in dist.items() if v}
    return f"Pipeline distribution: {active or 'no candidates tracked'}."


def _summarize_dashboard(output: Dict[str, Any]) -> str:
    skills = output.get("top_skills", [])[:5]
    skill_str = ", ".join(f"{s}({c})" for s, c in skills) if skills else "n/a"
    return (
        f"Cohort: {output.get('candidate_count', 0)} candidates, avg experience "
        f"{output.get('average_experience', 0)} yrs. Top skills: {skill_str}."
    )


def _summarize_explainability(output: Dict[str, Any]) -> str:
    reasons = output.get("reasons", [])
    tail = f" Reasons: {'; '.join(reasons)}." if reasons else ""
    return f"Rule-based ranking total {output.get('total_score', 'n/a')}.{tail}"


def _summarize_resume_analysis(output: Dict[str, Any]) -> str:
    dims = output.get("dimensions", {})
    strengths = output.get("strengths", [])
    weaknesses = output.get("weaknesses", [])
    improvements = output.get("top_improvements", [])
    lines = [
        f"Resume quality {output.get('overall_quality', 0):.0f}/100 "
        f"(structure {dims.get('structure', 0):.0f}, writing {dims.get('writing', 0):.0f}, "
        f"technical {dims.get('technical_depth', 0):.0f}, ATS "
        f"{output.get('ats_friendliness', 'n/a')}). This is resume quality, not a hiring score.",
    ]
    if strengths:
        lines.append("Strengths: " + "; ".join(strengths[:3]) + ".")
    if weaknesses:
        lines.append("Weaknesses: " + "; ".join(weaknesses[:3]) + ".")
    if output.get("risk_findings"):
        lines.append(f"Resume risk: {output.get('risk_level')} ({len(output['risk_findings'])} finding(s)).")
    if improvements:
        tops = ", ".join(f"{i['title']} ({i['priority']})" for i in improvements[:3])
        lines.append("Top improvements: " + tops + ".")
    return "\n".join(lines)


def _summarize_jd_analysis(output: Dict[str, Any]) -> str:
    dims = output.get("dimensions", {})
    lines = [
        f"JD quality {output.get('overall_quality', 0):.0f}/100 "
        f"(role clarity {dims.get('role_clarity', 0):.0f}, technical clarity "
        f"{dims.get('technical_clarity', 0):.0f}, requirement quality "
        f"{dims.get('requirement_quality', 0):.0f}). This is JD quality, not a candidate score.",
        f"Inferred role: {output.get('seniority', '?')} · {output.get('technical_level', '?')} "
        f"(confidence {output.get('role_confidence', 0):.0f}%).",
        f"Likely hiring intent: {output.get('primary_intent', '?')} "
        f"({output.get('intent_confidence', 0):.0f}% confidence) — inference, not stated fact.",
    ]
    mandatory = output.get("mandatory", [])
    if mandatory:
        lines.append("Mandatory: " + "; ".join(mandatory[:3]) + ".")
    if output.get("risk_findings"):
        lines.append(f"JD risk: {output.get('risk_level')} ({len(output['risk_findings'])} finding(s)).")
    improvements = output.get("top_improvements", [])
    if improvements:
        tops = ", ".join(f"{i['title']} ({i['priority']})" for i in improvements[:3])
        lines.append("Top improvements: " + tops + ".")
    return "\n".join(lines)


def _summarize_committee(output: Dict[str, Any]) -> str:
    lines = [
        f"**Committee decision: {output.get('recommendation', 'n/a')}** "
        f"({output.get('consensus_level', 'n/a')}, confidence "
        f"{output.get('overall_confidence', 0):.0f}/100).",
    ]
    opinions = output.get("opinions", [])
    if opinions:
        panel = "; ".join(f"{o['role']}: {o['recommendation']}" for o in opinions)
        lines.append("Panel: " + panel + ".")
    disagreements = output.get("disagreements", [])
    if disagreements:
        lines.append("Disagreement: " + " ".join(disagreements))
    conflicts = output.get("conflicts", [])
    if conflicts:
        lines.append(
            "Key conflict(s): "
            + "; ".join(c["between"] for c in conflicts[:3])
            + "."
        )
    risks = output.get("hiring_risks", [])
    if risks:
        lines.append("Risks: " + "; ".join(risks[:3]) + ".")
    unknowns = output.get("remaining_unknowns", [])
    if unknowns:
        lines.append("Remaining unknowns: " + "; ".join(unknowns[:2]) + ".")
    actions = output.get("follow_up_actions", [])
    if actions:
        lines.append("Next steps: " + "; ".join(actions[:3]) + ".")
    return "\n".join(lines)


def _summarize_executive_report(output: Dict[str, Any]) -> str:
    lines = [
        f"**{output.get('template_name', 'Executive')} report for {output.get('candidate_id', '?')}** — "
        f"recommends **{output.get('overall_recommendation', 'n/a')}** → action "
        f"'{output.get('recommended_action', 'n/a')}' "
        f"(executive confidence {output.get('executive_confidence', 'n/a')}).",
    ]
    if output.get("executive_summary"):
        lines.append(output["executive_summary"])
    reasons = output.get("top_reasons", [])
    if reasons:
        lines.append("Top reasons: " + "; ".join(reasons[:3]) + ".")
    concerns = output.get("top_concerns", [])
    if concerns:
        lines.append("Top concerns: " + "; ".join(concerns[:3]) + ".")
    fmt = output.get("format", "pdf")
    if output.get("export_bytes_len"):
        lines.append(
            f"A {str(fmt).upper()} export ({output['export_bytes_len']:,} bytes) is ready to download. "
            "This report synthesizes existing intelligence — it introduces no new ranking."
        )
    elif output.get("export_error"):
        lines.append(f"(The {str(fmt).upper()} export could not be generated: {output['export_error']}.)")
    return "\n".join(lines)


def _summarize_interview_studio(output: Dict[str, Any]) -> str:
    lines = [
        f"**{output.get('role_name', 'Interview')} interview plan for {output.get('candidate_id', '?')}** "
        f"({output.get('depth', 'standard')} loop, {output.get('stage_count', 0)} stages, "
        f"{output.get('question_count', 0)} questions; readiness {output.get('readiness', 'n/a')}).",
    ]
    if output.get("interview_summary"):
        lines.append(output["interview_summary"])
    roadmap = output.get("roadmap", [])
    if roadmap:
        lines.append("Roadmap: " + " -> ".join(roadmap) + ".")
    probes = output.get("key_probes", [])
    if probes:
        lines.append("Key probes: " + "; ".join(probes[:3]) + ".")
    tech = output.get("technical_questions", [])
    if tech:
        lines.append("Sample technical questions: " + "; ".join(tech[:3]) + ".")
    validations = output.get("risk_validations", [])
    if validations:
        lines.append(
            "Risk validations: "
            + "; ".join(f"{v['risk']} -> {v['question']}" for v in validations[:2])
            + "."
        )
    bands = output.get("decision_bands", [])
    if bands:
        lines.append("Decision matrix bands: " + ", ".join(bands) + ".")
    lines.append("Every question traces back to existing intelligence; this plans the interview, it does not run it.")
    return "\n".join(lines)


def _summarize_compensation(output: Dict[str, Any]) -> str:
    lines = [
        f"**Compensation governance for {output.get('candidate_id', '?')}** — recommends "
        f"**{output.get('recommended_range', 'n/a')}** ({output.get('market_position', 'n/a')}, "
        f"{output.get('hire_type', 'n/a')}, {output.get('confidence', 'n/a')} confidence). "
        "This is a defensible range, not a salary prediction.",
    ]
    if output.get("executive_summary"):
        lines.append(output["executive_summary"])
    scenarios = output.get("scenarios", [])
    if scenarios:
        lines.append("Scenarios: " + "; ".join(f"{s['name']} {s['range']}" for s in scenarios[:4]) + ".")
    lines.append(
        f"Negotiation: acceptance {output.get('acceptance_likelihood', 'n/a')}, "
        f"probability {output.get('negotiation_probability', 'n/a')}."
    )
    strategy = output.get("negotiation_strategy", [])
    if strategy:
        lines.append("Strategy: " + "; ".join(strategy[:2]) + ".")
    justifications = output.get("key_justifications", [])
    if justifications:
        lines.append("Justification: " + "; ".join(justifications[:3]) + ".")
    assumptions = output.get("key_assumptions", [])
    if assumptions:
        lines.append("Assumptions: " + "; ".join(assumptions[:2]) + ".")
    lines.append(f"Market data: {output.get('market_data_note', 'internal heuristic model')}")
    lines.append(f"Internal equity: {output.get('internal_equity', 'unavailable')}")
    lines.append(
        f"Audit trail {output.get('audit_decision_id', 'n/a')} — approvals: "
        f"{', '.join(output.get('approvals_required', []))} "
        f"({output.get('human_review_status', 'pending')})."
    )
    return "\n".join(lines)


def _summarize_pay_equity(output: Dict[str, Any]) -> str:
    lines = [
        f"**Pay-equity review for {output.get('candidate_id', '?')}** — equity risk "
        f"**{output.get('equity_risk', 'n/a')}**"
        + ("" if output.get("data_available") else " (no internal data — provisional)")
        + f"; compression {output.get('compression_risk', 'n/a')}, inversion "
        f"{output.get('inversion_risk', 'n/a')}. Governance assessment only — no legal conclusion.",
    ]
    if output.get("executive_summary"):
        lines.append(output["executive_summary"])
    lines.append(output.get("data_availability_note", ""))
    lines.append(
        f"Policy '{output.get('policy', 'n/a')}': {output.get('policy_alignment', 'n/a')}."
        + (" Violations: " + "; ".join(output.get("policy_violations", [])) if output.get("policy_violations") else "")
    )
    approvers = output.get("required_approvers", [])
    if approvers:
        lines.append(f"{output.get('review_level', 'Standard')} review — approvers: {', '.join(approvers)}.")
    recs = output.get("human_review_recommendations", [])
    if recs:
        lines.append("Human review: " + "; ".join(recs[:3]) + ".")
    return "\n".join(l for l in lines if l)


def _summarize_compliance(output: Dict[str, Any]) -> str:
    lines = [
        f"**Hiring compliance for {output.get('candidate_id', '?')}** — workflow "
        f"**{output.get('workflow_status', 'n/a')}** "
        f"({output.get('workflow_completed', 0)}/{output.get('workflow_total', 0)} steps), "
        f"governance risk {output.get('governance_risk', 'n/a')}, audit {output.get('audit_status', 'n/a')}. "
        "Governance assessment only — not legal advice.",
    ]
    if output.get("executive_summary"):
        lines.append(output["executive_summary"])
    outstanding = output.get("outstanding_approvals", [])
    if outstanding:
        lines.append("Outstanding approvals: " + ", ".join(outstanding) + ".")
    missing_docs = output.get("missing_documentation", [])
    if missing_docs:
        lines.append("Missing documentation: " + ", ".join(missing_docs) + ".")
    exceptions = output.get("exceptions", [])
    real = [e for e in exceptions if e.get("kind") != "No exceptions detected"]
    if real:
        lines.append("Exceptions: " + "; ".join(f"{e['kind']} ({e['severity']})" for e in real[:4]) + ".")
    policies = [p for p in output.get("policy_checks", []) if p.get("status") not in ("Not Applicable",)]
    if policies:
        lines.append("Policy: " + "; ".join(f"{p['policy']}: {p['status']}" for p in policies[:4]) + ".")
    if output.get("reviewers"):
        lines.append(f"Recommend {', '.join(output['reviewers'])} review.")
    actions = output.get("required_actions", [])
    if actions:
        lines.append("Required actions: " + "; ".join(actions[:3]) + ".")
    return "\n".join(lines)


def _summarize_audit(output: Dict[str, Any]) -> str:
    lines = [
        f"**Hiring-decision audit for {output.get('candidate_id', '?')}** — "
        f"{output.get('agent_count', 0)} AI agent(s) participated; audit readiness "
        f"**{output.get('audit_readiness', 'n/a')}** ({output.get('readiness_level', 'n/a')}). "
        "Reconstructed from artefacts on record; no fabrication, no legal opinion.",
    ]
    if output.get("executive_summary"):
        lines.append(output["executive_summary"])
    trace = [t for t in output.get("decision_trace", []) if t.get("status") == "Observed"]
    if trace:
        lines.append("Decision journey: " + " -> ".join(t["stage"] for t in trace) + ".")
    ai = output.get("ai_decisions", [])
    if ai:
        lines.append("AI decisions: " + "; ".join(ai[:4]) + ".")
    human = output.get("human_decisions_verified", [])
    lines.append(
        "Verified human approvals: " + (", ".join(human) if human else "none on record (pending review).")
    )
    outstanding = output.get("outstanding_approvals", [])
    if outstanding:
        lines.append("Outstanding approvals: " + ", ".join(outstanding) + ".")
    risks = output.get("outstanding_risks", [])
    if risks:
        lines.append("Outstanding audit gaps: " + "; ".join(risks[:3]) + ".")
    if not output.get("history_available"):
        lines.append("(No historical audit archive connected — showing the current decision only.)")
    return "\n".join(lines)


def _summarize_hiring_intelligence(output: Dict[str, Any]) -> str:
    lines = [
        f"**Workforce hiring intelligence** over {output.get('cohort_size', 0)} analyzed candidate(s) — "
        f"Hiring Health **{output.get('hiring_health', 'n/a')}**"
        + (f" ({output.get('hiring_health_value'):.0f}/100)" if isinstance(output.get('hiring_health_value'), (int, float)) else "")
        + ". Organizational intelligence only — never candidate ranking; no fabricated statistics.",
    ]
    if output.get("executive_summary"):
        lines.append(output["executive_summary"])
    kpis = [k for k in output.get("kpis", []) if k.get("register") == "Observed"]
    if kpis:
        lines.append("KPIs: " + "; ".join(f"{k['name']}: {k['label']}" for k in kpis) + ".")
    bottlenecks = output.get("estimated_bottlenecks", [])
    if bottlenecks:
        lines.append("Estimated bottlenecks: " + "; ".join(f"{b['stage']} ({b['severity']})" for b in bottlenecks) + ".")
    opts = [o for o in output.get("optimizations", []) if o.get("priority") in ("Critical", "High")]
    if opts:
        lines.append("Priority optimizations: " + "; ".join(o["recommendation"] for o in opts[:3]) + ".")
    unavailable = output.get("unavailable_trends", [])
    if unavailable and not output.get("data_available"):
        lines.append(
            f"{len(unavailable)} trend(s) UNAVAILABLE — no workforce-analytics source connected (connect one to unlock time-series)."
        )
    return "\n".join(lines)


_SUMMARIZERS = {
    "faiss_search": _summarize_search,
    "candidate_search": _summarize_search,
    "candidate_intelligence": _summarize_intelligence,
    "timeline": _summarize_timeline,
    "risk": _summarize_risk,
    "recommendation": _summarize_recommendation,
    "interview": _summarize_interview,
    "skill_gap": _summarize_skill_gap,
    "comparison": _summarize_comparison,
    "pipeline": _summarize_pipeline,
    "dashboard": _summarize_dashboard,
    "explainability": _summarize_explainability,
    "resume_analysis": _summarize_resume_analysis,
    "jd_analysis": _summarize_jd_analysis,
    "hiring_committee": _summarize_committee,
    "executive_report": _summarize_executive_report,
    "interview_studio": _summarize_interview_studio,
    "compensation_governance": _summarize_compensation,
    "pay_equity_guardian": _summarize_pay_equity,
    "hiring_compliance": _summarize_compliance,
    "hiring_audit": _summarize_audit,
    "hiring_intelligence": _summarize_hiring_intelligence,
}

_INTENT_LEAD = {
    "Search Candidate": "Here are the candidates that best match your search.",
    "Skill Search": "Here are the candidates matching the requested skills.",
    "Compare Candidates": "Here is how the candidates compare on the deterministic metrics.",
    "Explain Ranking": "Here is why this candidate ranks where they do.",
    "Generate Hiring Summary": "Here is the hiring summary based on the intelligence engines.",
    "Analyze Candidate": "Here is a structured analysis of the candidate.",
    "Generate Interview Plan": "Here is a structured interview plan.",
    "Pipeline Question": "Here is the pipeline status.",
    "Dashboard Question": "Here is the cohort overview.",
    "Recommendation Question": "Here is the hiring recommendation and its basis.",
    "Resume Review": "Here is a recruiter-grade review of the resume's quality (not a hiring decision).",
    "JD Analysis": "Here is an enterprise analysis of the job description's quality, intent and risks.",
    "Hiring Committee": "The AI Hiring Committee convened, debated the evidence and reached a decision.",
    "Executive Report": "Here is the executive hiring report, synthesizing every existing intelligence source.",
    "Interview Studio": "Here is the complete interview plan, personalized from every existing intelligence source.",
    "Compensation Governance": "Here is the transparent, defensible compensation governance analysis — evidence, reasoning and a full audit trail.",
    "Pay Equity": "Here is the internal pay-equity and fairness review — governance risks and human-review needs only, never a legal conclusion.",
    "Hiring Compliance": "Here is the hiring-compliance governance review — workflow, approvals, policy, documentation and audit readiness. It supports compliance; it is not legal advice.",
    "Hiring Audit": "Here is the reconstructed hiring-decision journey — decision trace, evidence provenance, human vs AI responsibility and audit readiness. It reconstructs the record; it gives no legal opinion.",
    "Hiring Intelligence": "Here is the enterprise workforce hiring intelligence — hiring health, KPIs, bottlenecks and optimization opportunities. Organizational intelligence only, with unavailable metrics marked honestly.",
    "General Hiring Question": "Here is guidance based on recruiting best practice.",
}


def compose_copilot_response(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically compose a :class:`CopilotResponse` from tool outputs."""
    intent = evidence.get("intent", "")
    tools: Dict[str, Any] = evidence.get("tools", {}) or {}

    lead = _INTENT_LEAD.get(intent, "Here is what the deterministic engines report.")
    sections: List[str] = []
    evidence_sources: List[str] = []

    for name, output in tools.items():
        summarizer = _SUMMARIZERS.get(name)
        if summarizer is None or not isinstance(output, dict):
            continue
        if output.get("error"):
            continue
        sections.append(summarizer(output))
        if name in _TOOL_EVIDENCE:
            evidence_sources.append(_TOOL_EVIDENCE[name])

    if sections:
        answer = lead + "\n\n" + "\n\n".join(sections)
    else:
        answer = (
            f"{lead} I don't have specific tool evidence for this request yet — "
            "please name a candidate or provide a search query so I can pull the "
            "relevant deterministic intelligence."
        )

    reasoning_summary = (
        f"Derived from {len(sections)} tool output(s): "
        f"{', '.join(dict.fromkeys(evidence_sources)) or 'none'}."
    )

    # Confidence / uncertainty.
    risk = tools.get("risk", {})
    intel = tools.get("candidate_intelligence", {})
    low_confidence = (
        (isinstance(intel, dict) and intel.get("confidence", 100) < 55)
        or (isinstance(risk, dict) and risk.get("risk_level") == "High")
        or not sections
    )
    confidence_note = (
        "Confidence is limited — evidence is thin or risk is elevated; validate "
        "before acting."
        if low_confidence
        else "Confidence is solid — the engine signals are consistent."
    )

    return {
        "answer": answer,
        "reasoning_summary": reasoning_summary,
        "evidence_sources": list(dict.fromkeys(evidence_sources)),
        "confidence_note": confidence_note,
    }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class RecruiterCopilotAgent(BaseAgent):
    """Turns structured tool outputs into a recruiter-quality answer."""

    metadata = AgentMetadata(
        name="recruiter_copilot",
        version="v1",
        title="Recruiter Copilot",
        description=(
            "Narrates the deterministic engines' tool outputs into professional, "
            "evidence-based recruiter answers. Never scores or fabricates."
        ),
        prompt_id="recruiter_copilot",
        prompt_version="v1",
        tags=["copilot", "recruiter", "reasoning"],
    )
    output_schema = CopilotResponse

    def build_evidence(self, payload: RecruiterCopilotInput) -> Dict[str, Any]:
        """Return the structured evidence (intent + message + tool outputs)."""
        return build_evidence(payload)

    def prompt_values(
        self, payload: RecruiterCopilotInput, evidence: Dict[str, Any]
    ) -> Dict[str, str]:
        """Supply the recruiter message + intent placeholders."""
        return {"recruiter_message": payload.message, "intent": payload.intent}

    def cache_dimensions(self, payload: RecruiterCopilotInput) -> Tuple[str, str]:
        """Cache by intent (subject) and message + tool-output signature (scope)."""
        signature = json.dumps(payload.tool_outputs, sort_keys=True, default=str)
        return payload.intent or "general", f"{payload.message}||{signature}"


register_composer(CopilotResponse.schema_name(), compose_copilot_response)
recruiter_copilot_agent = registry.register(RecruiterCopilotAgent())
