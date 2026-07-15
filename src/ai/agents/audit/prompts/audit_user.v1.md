Author the hiring-audit / explainability narrative for candidate: {{candidate_id}}

Agents participated: {{agents_participated}}
Audit readiness: {{audit_readiness}}    Historical archive connected: {{data_available}}

## Reconstructed audit evidence (authoritative — do not contradict or extend)

This is the reconstructed decision journey assembled from artefacts the platform
already produced — the decision trace, evidence provenance, evidence graph,
reasoning registers, timeline, human-vs-AI responsibility matrix, governance
explanations and audit readiness. Reason ONLY over what is present here.
"Unavailable" means that step/artefact is not on record.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 sentences an executive/auditor reads first — can the
  hiring journey be reconstructed, which agents participated, and how audit-ready
  it is. State plainly this reconstructs the record and gives no legal opinion.
- `decision_journey_note`: the chronological trace of what happened.
- `evidence_note`: which evidence influenced the decision and its provenance.
- `responsibility_note`: separate AI recommendations from human decisions/approvals
  clearly — never blur responsibility.
- `governance_note`: why the governance events (approvals, committee, compensation,
  equity, compliance) occurred.
- `readiness_note`: audit readiness — missing evidence/documents/approvals and
  unverified decisions.
- `data_availability_note`: exactly what was and was not on record (e.g. no
  historical archive connected).
- `key_findings` / `assumptions` / `audit_recommendations` / `outstanding_risks`:
  concise, evidence-anchored bullets; label assumptions and mark unverified items.
- `confidence_note`: your confidence and explicit uncertainty where data is missing.

Return only the JSON object.
