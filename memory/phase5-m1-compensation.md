---
name: phase5-m1-compensation
description: TalentMind Phase 5/M1 CompensationGovernanceAgent — compensation transparency system at src/ai/agents/compensation
metadata:
  type: project
---

Phase 5 / Milestone 1 built the **Enterprise Compensation Governance System** at
`src/ai/agents/compensation/`, mirroring the interview-studio/executive-report
pattern ([[phase4-m5-interview-studio]]). NOT a salary predictor — it explains,
justifies, documents and governs a compensation recommendation from existing
intelligence. Consumes cached outputs; modifies no engine. Non-obvious facts:

- **Reuses committee `gather_evidence`:** `CompensationGovernanceEngine.build()`
  (`governance.py`) calls `src.ai.committee.committee.gather_evidence(...)`, runs
  committee, then assembles. Also reads the candidate's OWN
  `redrob_signals.expected_salary_range_inr_lpa` (SalaryRange min/max, INR LPA) +
  offer_acceptance_rate/notice_period/willing_to_relocate as Observed Evidence.
- **Score-free constraint:** `CompensationNarrative` (BaseAIResponse) is qualitative
  prose only; ALL numbers (ranges, confidence) live in nested dataclasses. Range is
  min/target/max — NEVER a single figure (Module 1).
- **Internal heuristic model, no fabrication (Module 16):** `pay_band.derive_pay_band`
  anchors on the candidate's stated expectation + internal premium multipliers
  (`templates.PREMIUM_FACTORS`: skill/leadership/strategic/risk). No market survey.
  Market position always carries "Recommendation based on internal heuristic model."
- **Internal equity (Module 8/14):** `internal_equity.py` — `CompensationDataProvider`
  Protocol + `NullCompensationDataProvider` default → "Internal equity validation
  unavailable." Inject a real provider to evaluate pay-band/compression. NO payroll
  connectors implemented; HRIS_CONNECTORS names registered as extension points only.
- **Flagship audit trail (Module 12):** `offer_justification.build_audit_trail` →
  AuditTrail (decision_id "COMP-...", timestamp=injected generated_on, evidence
  sources, agents_consulted, reasoning_chain, approvals_required, human_review_status).
  `.to_export_text()` exportable. Critical Hire (strong committee stance) escalates
  approvals to add Executive Sponsor. Offer justification entries tagged
  Evidence/Reasoning/Business Impact/Assumption.
- **Auto-registration on import of agent.py:** AI registry (`compensation_governance`)
  + composer + orchestration (RunnerAgent). Own prompt loader.
- **Copilot (additive):** NEW `Intent.COMPENSATION_GOVERNANCE`. Patterns avoid
  colliding with EXECUTIVE_REPORT ("generate report"/"create report" not substrings
  of "generate compensation report"). `compensation_tools.py` +
  `_summarize_compensation` narrator + follow-ups + single_intents.
- **UI:** `src/ui/compensation_tab.render_compensation_workspace()` wired as 9th
  app.py workspace ("Compensation Governance"); 12 tabs incl. audit-trail export.
- **cp1252 gotcha:** keep non-ASCII (en-dash) out of strings that hit the Windows
  console/logs; `CompensationRange.formatted()` uses ASCII hyphen (en-dash only in
  Streamlit UI metrics, which is fine).

Tests: `pytest tests/ -p no:faulthandler` → 312 passing (adds test_compensation.py=35,
test_compensation_ui.py=2). See PHASE5_MILESTONE1_REPORT.md.
