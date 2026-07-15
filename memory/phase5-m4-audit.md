---
name: phase5-m4-audit
description: TalentMind Phase 5/M4 HiringAuditAgent — audit & explainability platform at src/ai/agents/audit
metadata:
  type: project
---

Phase 5 / Milestone 4 built the **Enterprise Hiring Audit & Explainability
Platform** at `src/ai/agents/audit/`, capstone of the governance stack. Reconstructs
the complete hiring decision journey. NOT logging, NOT observability, NOT legal
opinion. Non-obvious facts:

- **Reuses the WHOLE chain via Hiring Compliance:** `HiringAuditEngine.build()`
  (`audit_engine.py`) runs `HiringComplianceEngine` (which reuses pay equity → comp
  → committee → gather_evidence) — ONE call. Augments evidence_sources with
  "Hiring Compliance". Accepts TWO injected providers: `compliance_provider` (passed
  down to compliance for approvals/docs) + `archive_provider` (Module 8 history).
- **Agent catalog label gotcha:** `templates.AGENT_CATALOG` source labels MUST match
  what the chain actually emits. Risk is emitted as **"Resume Risk Detection"** (the
  compensation validators' label), NOT the committee's "Risk Intelligence". Got this
  wrong first; the audit trace showed Risk Unavailable until fixed. Participation/
  provenance/graph all derive from evidence_sources membership.
- **Human vs AI never blurred (Module 5):** `approvals.build_responsibility_matrix`
  = AI decisions (committee/comp/pay-equity/compliance, responsible_party "AI") +
  `human_review.build_human_decisions` (approver roles). Human approvals are
  "Unverified" without a connected system — NEVER "Observed". Safety guard asserts this.
- **Score-free schema:** `AuditNarrative` (BaseAIResponse) qualitative prose.
- **Safety guard assertion-specific** (`validators.validate_safety`): flags "our
  legal opinion is"/"is illegal"/"we rule that"; also flags human decision Observed
  without archive + history available without archive. (Same disclaimer-safe lesson
  as m2/m3.)
- **5 registers:** Observed / Unavailable / Inferred / Recommendation / Human Review.
- **Auto-registration on import of agent.py:** AI registry (`hiring_audit`) +
  composer + orchestration (RunnerAgent). Own prompt loader.
- **Copilot (additive):** NEW `Intent.HIRING_AUDIT`. Patterns coexist with all prior
  governance intents: "show audit trail"→COMPLIANCE (7) but "generate audit
  report"→AUDIT; "why was this candidate hired"→AUDIT but "why is this candidate
  ranked"→EXPLAIN_RANKING; dropped bare "evidence"/"approval chain" to avoid ties
  with committee/pay-equity. `audit_tools.py` + narrator + follow-ups.
- **UI:** `src/ui/audit_tab.render_audit_workspace()` wired as 12th app.py workspace
  ("Hiring Audit"); 11 tabs.

Tests: `pytest tests/ -p no:faulthandler` → 412 (adds test_audit.py=30,
test_audit_ui.py=2). See PHASE5_MILESTONE4_REPORT.md. Governance stack now:
Compensation → Pay Equity → Compliance → Audit, each reusing the one below.
