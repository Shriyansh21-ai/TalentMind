Author the internal pay-equity fairness narrative for candidate: {{candidate_id}}

Offer under review: {{offer_summary}}
Company pay policy: {{policy_name}}    Internal data available: {{data_available}}

## Aggregated intelligence (authoritative — do not contradict or extend)

This is the collected structured output of TalentMind's existing engines — the
Compensation Governance recommendation, candidate intelligence, timeline, risk,
committee and recommendation — plus the pay-equity signals already computed
(compression, inversion, promotion equity, policy alignment, executive review)
and, when present, connected internal compensation data. Reason ONLY over what is
present here. Empty objects / "unavailable" mean that source was not connected.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 sentences an HR/Finance partner reads first — is the
  offer internally fair, what (if anything) needs review, and whether internal data
  was available. State plainly this is a governance assessment, not a legal finding.
- `equity_assessment`: restate the internal-equity findings and their WHY.
- `compression_note` / `inversion_note`: restate the risk levels. If data is
  unavailable, say "Company compensation data unavailable." / "Unable to evaluate
  without internal compensation data." — never invent payroll.
- `promotion_note`: promotion/level alignment and progression.
- `policy_note`: alignment with the named policy; "violation" means an internal
  policy exception routed for review, never a legal violation.
- `fairness_note`: potential concerns and the human-review recommendations; never
  accuse discrimination, never conclude a legal violation.
- `review_note`: who should approve and why (Recruiter / Hiring Manager / HR /
  Finance / Legal / Executive).
- `data_availability_note`: exactly what internal data was and was not available.
- `key_findings` / `assumptions` / `human_review_recommendations`: concise,
  evidence-anchored bullets; label assumptions explicitly.
- `confidence_note`: your confidence and explicit uncertainty when data is thin.

Return only the JSON object.
