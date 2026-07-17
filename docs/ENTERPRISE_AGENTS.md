# TalentMind — Enterprise Agents

Every AI agent in TalentMind follows the same contract:

- subclasses `BaseAgent` (`src/ai/core/base_agent.py`);
- renders versioned prompts from its own `prompts/` directory;
- registers on import with (a) the core `registry`, (b) the deterministic composer registry
  (`providers/composers.py`), and (c) the orchestration registry via `RunnerAgent`;
- is **score-free** (enforced by `SafetyGuard`), **offline-capable**, and **deterministic in
  offline mode** (the composer is a pure function of evidence).

Agents **consume already-computed engine outputs and never re-rank candidates.** Governance agents
(pay equity, compliance, audit) additionally disclaim legal conclusions and are *data-gated* —
they mark unavailable data honestly instead of inventing it.

See [`AI_PLATFORM.md`](AI_PLATFORM.md) for the runner and safety model, and
[`MULTI_AGENT_SYSTEM.md`](MULTI_AGENT_SYSTEM.md) for orchestration and the committee.

---

## Agent roster

| Agent | Name | Module | Output schema |
|---|---|---|---|
| Hiring Analyst | `hiring_analyst` | `agents/hiring_analyst.py` | `HiringAnalysis` |
| Resume Analyst | `resume_analyst` | `agents/resume/agent.py` | `ResumeAnalysis` |
| JD Analyst | `jd_analyst` | `agents/jd/agent.py` | `JDAnalysis` |
| Interview Studio | `interview_studio` | `agents/interview_studio/agent.py` | `InterviewStudioNarrative` |
| Executive Hiring Report | `executive_hiring_report` | `agents/executive_report/agent.py` | `ExecutiveNarrative` |
| Compensation Governance | `compensation_governance` | `agents/compensation/agent.py` | `CompensationNarrative` |
| Pay Equity Guardian | `pay_equity_guardian` | `agents/pay_equity/agent.py` | `PayEquityNarrative` |
| Hiring Compliance | `hiring_compliance` | `agents/compliance/agent.py` | `ComplianceNarrative` |
| Hiring Audit | `hiring_audit` | `agents/audit/agent.py` | `AuditNarrative` |
| Hiring Intelligence | `hiring_intelligence` | `agents/hiring_intelligence/agent.py` | `WorkforceNarrative` |
| Recruiter Copilot | `recruiter_copilot` | `agents/recruiter_copilot.py` | `CopilotResponse` |
| Committee Chair | `committee_chair` | `committee/chair.py` | `CommitteeDecision` |

---

## Hiring Analyst — `hiring_analyst`

- **Purpose** — reason over deterministic engine output to produce an executive-quality narrative
  hiring analysis.
- **Inputs** — `HiringAnalystInput(insights: CandidateInsights, interview_plan: InterviewPlan, jd="")`.
- **Outputs** — `HiringAnalysis` (`schemas/hiring_analysis.py`): executive summary, overall /
  technical / career / leadership / risk reasoning, JD alignment, hidden strengths & concerns,
  transferable skills, interview strategy, business impact, confidence reasoning, and
  `executive_decision ∈ EXECUTIVE_DECISIONS`. **No numeric fields.**
- **Deterministic engines used** — Candidate Intelligence, Career Timeline, Risk, Hiring
  Recommendation, Interview Plan, skill gap (all via `insights` + `interview_plan`).
- **Reasoning flow** — evidence bundle → prompt render → provider (`local` composer
  `compose_hiring_analysis`) → schema validation.
- **Safety** — "never computes or overrides a score — the schema has no numeric fields and the
  composer only restates the evidence"; explicit uncertainty when evidence is thin.
- **Integration** — cached by candidate id + JD; exposed via `services/hiring_analyst_service.py`.

## Resume Analyst — `resume_analyst`

- **Purpose** — recruiter-grade resume-*quality* intelligence: structure, writing, technical
  depth, projects, achievements, ATS coverage, career story, evidence-based risks.
- **Inputs** — `ResumeAnalystInput(candidate_id, candidate, resume_text, jd)`.
- **Outputs** — `ResumeAnalysis` (`resume/schemas.py`).
- **Deterministic engines used** — internal pipeline `extractors → metrics → validators →
  composer` (`resume/`).
- **Safety** — "resume quality only, never hiring ranking"; JD used only for ATS keyword coverage,
  never for ranking; evidence contains nothing the AI may invent.
- **Integration** — orchestration capabilities `resume_analysis`, `resume_review`.

## JD Analyst — `jd_analyst`

- **Purpose** — enterprise job-description intelligence: role level, technical shape, hiring
  intent, org context, requirement hierarchy, market posture, quality, risk.
- **Inputs** — `JDAnalystInput(jd_text, jd_id, title)`.
- **Outputs** — `JDAnalysis` (`jd/schemas.py`).
- **Deterministic engines used** — pipeline `extractors → metrics → validators → report →
  composer` + offline market estimates.
- **Safety** — "JD quality only, never candidate ranking"; market estimates are offline; nothing
  invented.
- **Integration** — cached by jd_id + text hash; capabilities `jd_analysis`, `jd_review`.
  `analysis_interfaces.py` provides a logic-free seam for a future Fit/Match agent — the two
  analysts remain independent.

## Interview Studio — `interview_studio`

- **Purpose** — transform existing intelligence into a complete personalized interview plan:
  strategy, adaptive question flow, evaluation rubrics, interviewer guides, feedback templates,
  decision matrix.
- **Inputs** — `InterviewStudioInput(candidate_id, role, role_name, depth, candidate_overview,
  resume, jd, committee, intelligence, timeline, risk, recommendation, interview)` — all
  pre-computed dicts, all optional.
- **Outputs** — `InterviewStudioNarrative` (`interview_studio/schemas.py`).
- **Safety** — "consumes existing outputs only; never re-ranks or invents; plans the interview, it
  does not run it"; degrades gracefully on missing sources.
- **Integration** — capabilities `interview_studio`, `interview_plan`, `interview_generation`.

## Executive Hiring Report — `executive_hiring_report`

- **Purpose** — synthesize all intelligence into a boardroom-grade one-page executive hiring
  narrative.
- **Inputs** — `ExecutiveReportInput(candidate_id, template, candidate_overview, resume, jd,
  committee, intelligence, timeline, risk, recommendation, interview, pipeline)`.
- **Outputs** — `ExecutiveNarrative` (`executive_report/schemas.py`).
- **Safety** — "consumes existing outputs only; never re-ranks or invents"; the template drives
  audience framing only.
- **Integration** — capabilities `executive_report`, `executive_hiring_report`. The package ships
  export renderers (`export/`: docx, html, pdf, ppt), `branding.py`, `builder.py`, `renderer.py`.

## Compensation Governance — `compensation_governance`

- **Purpose** — explain, justify, document, and govern a compensation recommendation for
  HR / Finance / Legal / executive approval.
- **Inputs** — `CompensationInput(candidate_id, candidate_overview, candidate_comp, resume, jd,
  committee, intelligence, timeline, risk, recommendation, interview, recommended_range,
  market_position, hire_type)`.
- **Outputs** — `CompensationNarrative` (`compensation/schemas.py`).
- **Deterministic engines used** — full AI ecosystem outputs + an engine-computed heuristic range
  (package modules: `pay_band`, `market_position`, `internal_equity`, `negotiation`,
  `offer_justification`, `budget`, `governance`, `future_growth`, `salary_strategy`,
  `executive_summary`).
- **Safety** — "**does not predict salaries**" — produces a defensible *range*, never a fixed
  salary; fabricates no salary or market data.

## Pay Equity Guardian — `pay_equity_guardian`

- **Purpose** — evaluate whether an offer is internally fair: salary compression, pay inversion,
  promotion equity, pay-policy alignment, executive-review needs.
- **Inputs** — `PayEquityInput(candidate_id, policy_name, data_available, …, compression,
  inversion, promotion, policy_alignment, fairness, executive_review)`.
- **Outputs** — `PayEquityNarrative` (`pay_equity/schemas.py`).
- **Data-gating** — `data_available` flag; provisional output when no internal comp data is
  connected; degrades gracefully.
- **Safety** — "**NOT a bias detector and NOT a legal decision engine**"; never fabricates
  payroll, never accuses discrimination, never concludes a legal violation.

## Hiring Compliance — `hiring_compliance`

- **Purpose** — evaluate whether a hiring workflow follows company governance: workflow steps,
  approval completeness, policy compliance, documentation, audit-trail readiness, governance risk.
- **Inputs** — `ComplianceInput(candidate_id, data_available, …, workflow, approvals,
  policy_checks, documentation, audit, governance_risk, exceptions, review)`.
- **Outputs** — `ComplianceNarrative` (`compliance/schemas.py`).
- **Data-gating** — yes.
- **Safety** — "**NOT a legal-advice system and NOT a law engine**"; never gives legal advice,
  interprets law, or fabricates a compliance conclusion.

## Hiring Audit — `hiring_audit`

- **Purpose** — reconstruct and explain the complete hiring decision journey: decision trace,
  evidence provenance, evidence graph, reasoning explainability, timeline, human-vs-AI
  responsibility, governance explanations, audit readiness.
- **Inputs** — `AuditInput(candidate_id, data_available, …, decision_trace, provenance, reasoning,
  timeline, responsibility, governance_explanations, audit_readiness, history)`.
- **Outputs** — `AuditNarrative` (`audit/schemas.py`).
- **Data-gating** — history archive optional.
- **Safety** — "reconstructs and explains — it never fabricates evidence, approvals, or history,
  never rewrites history, and never issues a legal opinion"; **clearly separates observed facts,
  inferred insights, AI recommendations, and human decisions.**

## Hiring Intelligence — `hiring_intelligence`

- **Purpose** — aggregate existing intelligence into strategic organizational analytics: hiring
  health, pipeline bottlenecks, team analytics, trends, executive KPIs, capacity, forecasts,
  benchmarks, optimization opportunities.
- **Inputs** — `HiringIntelligenceInput(cohort_size, data_available, analytics)`.
- **Outputs** — `WorkforceNarrative` (`hiring_intelligence/schemas.py`).
- **Data-gating** — marks unavailable metrics honestly.
- **Safety** — "**organizational intelligence only, never candidate ranking**"; fabricates no
  enterprise statistics, trends, KPIs, or forecasts.

## Recruiter Copilot — `recruiter_copilot`

- **Purpose** — narrate structured tool outputs into professional recruiter prose (the AI-Platform
  agent behind the conversational copilot).
- **Inputs** — `RecruiterCopilotInput(intent, message, tool_outputs)`.
- **Outputs** — `CopilotResponse` (`schemas/copilot_response.py`): answer, reasoning summary,
  evidence sources, confidence note (score-free).
- **Safety** — receives **only** structured tool outputs (never raw resumes or JSON dumps); never
  scores or fabricates; the offline composer cannot contradict the engines.

## Committee Chair — `committee_chair`

- **Purpose** — narrate and justify the committee's evidence-weighted consensus into an executive
  decision.
- **Inputs** — `ChairInput(candidate_overview, resume_summary, jd_summary, mode, opinions,
  consensus, conflicts, confidence, discussion)`.
- **Outputs** — `CommitteeDecision` (`committee/schemas.py`; score-free top level).
- **Safety** — "never re-decides or fabricates — grounded entirely in the deliberation"; the
  recommendation comes from the consensus, not chair fiat.

---

## Adding a new agent

Because orchestration is domain-free, a new agent needs no orchestration changes:

1. Create `src/ai/agents/<name>/` with `agent.py` (subclass `BaseAgent`), `schemas.py`
   (subclass `BaseAIResponse` — keep it **score-free**), and `prompts/<id>_system.v1.md` +
   `prompts/<id>_user.v1.md`.
2. Register a deterministic composer with `register_composer(schema_name, compose_fn)` so the
   agent works offline.
3. Implement `build_evidence`, `prompt_values`, and `cache_dimensions`.
4. Self-register on import (core registry + orchestration `RunnerAgent`).

See [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md#adding-new-agents) for the full walkthrough.
