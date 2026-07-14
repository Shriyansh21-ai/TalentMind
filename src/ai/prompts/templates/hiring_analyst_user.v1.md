Analyse the following candidate for the target role and return your hiring
analysis as a single JSON object.

## Target role (job description)

{{jd}}

## Structured evidence (authoritative — do not contradict or recompute)

The evidence below is the output of TalentMind's deterministic engines
(Candidate Intelligence, Career Timeline, Risk Detection, Hiring Recommendation
and the Interview Planner). Treat every value as ground truth.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Produce a hiring analysis with exactly these JSON fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 crisp sentences for a busy hiring leader.
- `*_reasoning` fields: interpret the corresponding evidence; explain *why* the
  signals look the way they do and what they mean for this role.
- `jd_alignment`: map the candidate's evidence to the job description explicitly.
- `hidden_strengths` / `hidden_concerns`: non-obvious signals implied by the
  evidence (never invented) — return short bullet strings.
- `transferable_skills`: skills in the evidence that transfer to the target role.
- `interview_strategy`: an ordered list of concrete, evidence-driven focus areas.
- `business_impact`: the expected impact if hired, grounded in the evidence.
- `confidence_reasoning`: how confident you are and why; call out thin evidence.
- `executive_decision`: one of "Strong Hire", "Hire", "Hold", "Reject", or
  "Insufficient Evidence". This is a narrative verdict; the canonical
  recommendation still comes from the deterministic engine.

Return only the JSON object.
