Author the hiring-compliance governance narrative for candidate: {{candidate_id}}

Workflow status: {{workflow_status}}    Governance risk: {{governance_risk}}
Governance data connected: {{data_available}}

## Aggregated intelligence (authoritative — do not contradict or extend)

This is the collected structured output of TalentMind's existing engines plus the
pre-computed compliance signals — the workflow steps, approval matrix, policy
checks, documentation review, audit findings, exceptions, governance risk and
review determination. Reason ONLY over what is present here. "Missing" /
"Requires Review" / "Needs Investigation" mean that item was not evidenced or
cannot be confirmed without an external system.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 sentences an HR/Compliance partner reads first — is the
  workflow compliant, what is missing, and whether Legal/Compliance should review.
  State plainly this is a governance assessment, not legal advice.
- `workflow_note`: which required steps are Completed / Missing / Requires Review.
- `approval_note`: which approvals are required and their completion state; explain
  why each is required.
- `policy_note`: results of the configured policy checks (governance findings, not
  legal opinions).
- `documentation_note`: which documents are present vs. missing; never invent one.
- `audit_note`: audit-trail readiness (evidence chain, agent participation,
  approval/decision history, human-review status).
- `risk_note`: the governance risk level and its drivers.
- `required_actions`: concrete governance actions to close gaps.
- `key_findings` / `assumptions` / `human_review_recommendations`: concise bullets;
  label assumptions explicitly and route items needing a person to human review.
- `confidence_note`: your confidence and explicit uncertainty where data is missing.

Return only the JSON object.
