Chair the hiring committee for candidate: {{candidate_id}}
Committee consensus recommendation: {{consensus_recommendation}}

## Committee deliberation (authoritative — do not contradict or extend)

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-3 sentences leadership can read first — the consensus
  level, the recommendation, and the headline reasoning.
- `recommendation`: echo the committee's evidence-weighted recommendation label.
- `business_justification` / `technical_justification`: ground each in the named
  members' opinions and evidence.
- `hiring_risks`: from the Risk Officer + any unresolved conflicts.
- `interview_priorities`: what the interview must validate (from the Interview Lead
  and open concerns).
- `remaining_unknowns`: missing evidence / abstentions / low-coverage areas.
- `follow_up_actions`: concrete next steps.
- `confidence_note`: explain the decision confidence and its drivers.

Return only the JSON object.
