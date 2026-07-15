Analyze the resume for candidate: {{candidate_id}}

Optional role context (for ATS keyword coverage only — never for ranking):
{{jd_context}}

## Resume evidence (authoritative — do not contradict or extend)

This is the deterministic extraction + metrics from TalentMind's resume engine.
Reason ONLY over what is present here.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-3 sentences a recruiter could read first — overall
  resume quality and the headline takeaway. State plainly this is resume quality,
  not a hiring decision.
- `strengths` / `weaknesses`: concrete, evidence-anchored bullet lists.
- `career_story`: narrative, direction, growth, consistency, focus, progression.
- `resume_quality`: the 0-100 dimensions (structure, writing, technical_depth,
  project_quality, achievements, ats_friendliness, professionalism,
  career_narrative, overall). Resume quality only.
- `structure`, `writing`, `technical`, `projects`, `achievements`, `ats_report`,
  `risk_report`: fill from the evidence; risks must cite evidence.
- `improvement_plan`: prioritized, high-impact-first recommendations with an
  example rewrite where useful.
- `confidence_note`: your confidence and any explicit uncertainty when evidence
  is thin.
- `evidence`: the concrete resume facts your analysis relied on.

Return only the JSON object.
