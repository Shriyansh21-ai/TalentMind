Author the executive hiring narrative for candidate: {{candidate_id}}

Target report template / audience framing: {{template}}

## Aggregated intelligence (authoritative — do not contradict or extend)

This is the collected structured output of TalentMind's existing engines and
agents — the committee decision, resume/JD analyses, candidate intelligence,
career timeline, risk report, interview plan and hiring recommendation. Reason
ONLY over what is present here. Empty objects mean that source was unavailable.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 sentences an executive could read first — who the
  candidate is, the headline recommendation and why. Attribute the
  recommendation to its source. State plainly this synthesizes existing
  intelligence, not a new hiring calculation.
- `overall_recommendation`: the qualitative label from the authoritative source
  (committee consensus if present, else the recommendation engine). A label,
  never a number.
- `business_impact` / `technical_impact` / `leadership_potential`: restate the
  committee's justifications and the intelligence/timeline signals; attribute.
- `risk_overview`: restate the Risk Intelligence posture and committee-flagged
  risks; do not invent risks.
- `interview_readiness`: restate the interview plan's priority areas.
- `executive_confidence`: a qualitative label (High / Moderate / Low) reflecting
  evidence coverage and consensus — not a hiring score.
- `top_reasons` / `top_concerns`: concise, evidence-anchored bullet lists drawn
  only from the reasons/strengths and risks/concerns already in the evidence.
- `confidence_note`: your confidence and any explicit uncertainty when evidence
  is thin.

Return only the JSON object.
