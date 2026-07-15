---
name: phase5-m2-pay-equity
description: TalentMind Phase 5/M2 PayEquityGuardianAgent — internal pay-equity/fairness system at src/ai/agents/pay_equity
metadata:
  type: project
---

Phase 5 / Milestone 2 built the **Enterprise Pay Equity Guardian** at
`src/ai/agents/pay_equity/`, mirroring the compensation-agent pattern
([[phase5-m1-compensation]]). Internal fairness/governance intelligence — NOT a
bias detector, NOT a legal engine. Non-obvious facts:

- **Reuses the Compensation Governance Agent for the offer:** `PayEquityGuardianEngine.build()`
  (`equity_engine.py`) runs `CompensationGovernanceEngine` to get the recommended
  range, then evaluates its internal fairness. No duplicated reasoning (Module 13).
- **Data-gated by design (Module 14):** WITHOUT an injected provider, compression/
  inversion report "Company compensation data unavailable." / "Unable to evaluate
  without internal compensation data.", equity risk = "Unknown", all 7 Module-1
  findings "Not Evaluable". Inject a `PayEquityDataProvider` (Protocol +
  `NullPayEquityDataProvider` default in equity_engine.py; duck-typed
  get_pay_band/get_peers/is_available) to evaluate real comparisons. NO connectors
  implemented; HRIS_PROVIDERS names (Workday/SuccessFactors/...) in templates only.
- **Score-free schema:** `PayEquityNarrative` (BaseAIResponse) qualitative prose;
  numbers/risk-levels in nested dataclasses.
- **Safety guard is ACCUSATION-specific:** `validators.validate_safety` scans for
  accusatory legal/discrimination phrases ("is discriminatory","discriminates
  against","illegal","lawsuit","guilty of") — NOT the bare stem "discriminat", so
  the system's own negating disclaimers ("makes no discrimination finding") don't
  trip it. Learned the hard way (first version flagged its own disclaimer).
- **Executive review (Module 7):** deterministic 6-role ladder — baseline
  Recruiter+HiringManager+HR; Finance if out-of-band/premium/critical; Legal if
  inversion or High compression (governance review, NOT a legal finding); Executive
  if High risk/policy violation/critical hire.
- **Policies (Module 5) are DATA** in `templates.PAY_POLICIES` (pay_band_first,
  market_first, performance_first, strategic_hire, critical_talent) with
  priority_factors + review_triggers; never hardcoded.
- **Auto-registration on import of agent.py:** AI registry (`pay_equity_guardian`)
  + composer + orchestration (RunnerAgent). Own prompt loader.
- **Copilot (additive):** NEW `Intent.PAY_EQUITY`. Patterns avoid COMPENSATION_GOVERNANCE
  collision (e.g. "who should approve" not bare "approval"; "create finance approval
  report" still -> COMPENSATION_GOVERNANCE). `pay_equity_tools.py` + narrator + follow-ups.
- **UI:** `src/ui/pay_equity_tab.render_pay_equity_workspace()` wired as 10th app.py
  workspace ("Pay Equity Guardian"); 10 tabs.

Tests: `pytest tests/ -p no:faulthandler` → 346 (adds test_pay_equity.py=32,
test_pay_equity_ui.py=2). NOTE: `test_app_boot.py` can TIMEOUT at 120s under full
parallel load (boots real 487MB dataset+FAISS+torch); passes standalone — not a
regression. See PHASE5_MILESTONE2_REPORT.md.
