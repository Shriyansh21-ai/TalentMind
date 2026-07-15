Author the compensation governance narrative for candidate: {{candidate_id}}

Recommended range (from the internal heuristic model): {{recommended_range}}
Market position: {{market_position}}    Hire type: {{hire_type}}

## Aggregated intelligence (authoritative — do not contradict or extend)

This is the collected structured output of TalentMind's existing engines and
agents — the candidate's stated expectation, resume/JD analyses, candidate
intelligence, career timeline, risk report, interview plan, hiring recommendation
and (when present) the committee decision — plus the heuristic compensation range
and governance signals already computed. Reason ONLY over what is present here.
Empty objects mean that source was unavailable.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 sentences a CHRO / Finance partner reads first — the
  recommended range, why it is defensible, and that it synthesizes existing
  intelligence rather than predicting a salary.
- `recommendation_rationale`: why this range, tracing to the candidate's stated
  expectation, seniority, skill/leadership signals and role fit. Attribute each.
- `market_position_note`: restate the market position. If no external market data
  is available, say "Recommendation based on internal heuristic model." — never
  invent benchmarks.
- `governance_note`: how the recommendation aligns with policy, role, experience
  and premiums; explain WHY.
- `negotiation_note`: acceptance likelihood and strategy, separating observed
  evidence (e.g. the candidate's stated expectation, acceptance rate) from advice.
- `budget_note`: hire type and investment rationale; flag every financial figure
  as a heuristic/assumption, never a fabricated metric.
- `internal_equity_note`: if payroll data is unavailable, state "Internal equity
  validation unavailable." Do not invent pay bands.
- `future_outlook_note`: promotion readiness and progression, with confidence.
- `transparency_note`: one sentence on the audit trail and required approvals.
- `key_justifications` / `key_assumptions`: concise, evidence-anchored bullets;
  assumptions must be explicitly labelled.
- `confidence_note`: your confidence and any explicit uncertainty when evidence is
  thin.

Return only the JSON object.
