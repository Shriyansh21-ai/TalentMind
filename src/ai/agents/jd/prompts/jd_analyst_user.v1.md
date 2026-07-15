Analyze the job description: {{jd_title}}  (id: {{jd_id}})

## JD evidence (authoritative — do not contradict or extend)

This is the deterministic extraction + metrics from TalentMind's JD engine.
Reason ONLY over what is present here.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-3 sentences a hiring manager could read first — overall
  JD quality and the headline takeaway. State plainly this is JD quality/intent,
  not a candidate ranking.
- `role_intelligence`: real seniority, technical level, ownership, leadership,
  decision-making, architecture, customer interaction, management, cross-functional
  — with a confidence.
- `technical_intelligence`: categorize the stack; comment on maturity + diversity.
- `hiring_intent`: infer why the role is open (growth / replacement / innovation /
  modernization / transformation / cost). EVERY signal must carry a confidence.
- `organization_intelligence`: estimate company type + maturity, with confidence.
- `requirement_hierarchy`: separate mandatory / preferred / nice-to-have / optional,
  plus hidden + implicit requirements.
- `market_intelligence`: heuristic, directional estimates, each with confidence.
- `quality`: the 0-100 JD-quality dimensions. JD quality only.
- `structure`, `risk_report`: fill from evidence; risks must cite evidence.
- `improvement_plan`: prioritized, high-impact-first recommendations with examples.
- `confidence_note`: overall confidence + explicit uncertainty where evidence is thin.
- `evidence`: the concrete JD facts your analysis relied on.

Return only the JSON object.
