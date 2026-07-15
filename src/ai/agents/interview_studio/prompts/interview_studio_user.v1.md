Author the interview strategy narrative for candidate: {{candidate_id}}

Target role path: {{role_name}}    Interview depth: {{depth}}

## Aggregated intelligence (authoritative — do not contradict or extend)

This is the collected structured output of TalentMind's existing engines and
agents — the committee decision, resume/JD analyses, candidate intelligence,
career timeline, risk report, the deterministic interview plan and the hiring
recommendation. Reason ONLY over what is present here. Empty objects mean that
source was unavailable.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `interview_summary`: 2-4 sentences an interview-panel lead reads first — who the
  candidate is, the shape of the loop and why it is designed this way. State
  plainly this synthesizes existing intelligence and validates it, rather than
  re-ranking the candidate.
- `strategy_overview`: how depth, difficulty and stages are calibrated to the
  seniority and role fit in the evidence.
- `recommended_focus`: the highest-priority things to probe, drawn from the
  committee's interview priorities and the recommendation engine's focus.
- `personalization_note`: exactly how THIS candidate's proven strengths and
  flagged development areas shaped the plan. Attribute to the source engine.
- `coverage_note`: what the loop covers (technical, system design, coding,
  behavioral, leadership, risk validation, debrief).
- `risk_validation_note`: how the flagged risks become validation questions; do
  not invent risks.
- `readiness_label`: a qualitative label reflecting evidence coverage and risk —
  never a number.
- `key_probes` / `watch_areas`: concise, evidence-anchored bullet lists drawn only
  from the priorities/strengths and risks/concerns already in the evidence.
- `confidence_note`: your confidence in the plan and any explicit uncertainty
  when evidence is thin.

Return only the JSON object.
