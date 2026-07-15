---
name: phase5-m3-compliance
description: TalentMind Phase 5/M3 HiringComplianceAgent — hiring governance/compliance system at src/ai/agents/compliance
metadata:
  type: project
---

Phase 5 / Milestone 3 built the **Enterprise Hiring Compliance Intelligence
System** at `src/ai/agents/compliance/`, mirroring the pay-equity pattern
([[phase5-m2-pay-equity]]). Governance/compliance over the hiring WORKFLOW — NOT
legal advice, NOT a law engine. Non-obvious facts:

- **Reuses the whole chain via Pay Equity Guardian:** `HiringComplianceEngine.build()`
  (`compliance_report.py`) runs `PayEquityGuardianEngine` (which transitively runs
  comp governance + committee + gather_evidence) — ONE call gives the full chain.
  The engine's `_context` appends "Compensation Governance Agent" + "Pay Equity
  Guardian" to `pe_report.evidence_sources` (pay equity's _sources does NOT include
  itself), else the pay_equity workflow-step/doc shows Missing.
- **Presence is DERIVED from evidence_sources** (e.g. "AI Hiring Committee" in
  sources → committee step Completed). Approval completion + externally-filed docs
  need the injected `ComplianceDataProvider` (Protocol + `NullComplianceDataProvider`
  default in compliance_report.py; duck-typed is_available/get_approvals/get_documents/
  get_audit_events). Without it: approvals "Requires Review", audit "Needs
  Investigation" — never assumed complete.
- **Approval matrix records provider approvals for ALL 6 roles** (not just the
  pay-equity-required set), so a policy requiring a non-required approver (e.g.
  above-threshold salary requires Finance) can see the provider's Complete state.
  `required` flag stays driven by pay equity. (Fixed a real bug here.)
- **Policies (Module 3) are DATA** in `templates.COMPLIANCE_POLICIES`
  (exec_hire_committee, critical_hire_exec, salary_threshold_finance,
  remote_documentation) with applies_when + requires tokens; policy_engine maps
  tokens to evidence. NEVER hardcoded. Threshold in COMPLIANCE_THRESHOLDS (50 LPA).
- **Score-free schema:** `ComplianceNarrative` (BaseAIResponse) qualitative prose.
- **Safety guard is ASSERTION-specific** (`validators.validate_safety`): catches
  "here is legal advice"/"our legal opinion is"/"is illegal"/"violates the law" but
  NOT the disclaimer "not legal advice" (same lesson as pay-equity's discrimination
  guard). Also flags any required approval marked Complete without a provider.
- **Auto-registration on import of agent.py:** AI registry (`hiring_compliance`) +
  composer + orchestration (RunnerAgent). Own prompt loader.
- **Copilot (additive):** NEW `Intent.HIRING_COMPLIANCE`. Patterns coexist with
  COMPENSATION_GOVERNANCE + PAY_EQUITY: "who should approve this"→PAY_EQUITY,
  "what approvals are missing"→COMPLIANCE, "show audit trail"→COMPLIANCE (weight 7
  beats comp's "audit trail" 5). `compliance_tools.py` + narrator + follow-ups.
- **UI:** `src/ui/compliance_tab.render_compliance_workspace()` wired as 11th app.py
  workspace ("Hiring Compliance"); 10 tabs. Kept non-ASCII arrows OUT of policy
  names (cp1252) — used "->".

Tests: `pytest tests/ -p no:faulthandler` → 380 (adds test_compliance.py=32,
test_compliance_ui.py=2). See PHASE5_MILESTONE3_REPORT.md.
