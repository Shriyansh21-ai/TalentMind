Recruiter message:
"{{recruiter_message}}"

Detected intent: {{intent}}

## Structured tool outputs (authoritative evidence — do not contradict)

These are the outputs of TalentMind's deterministic engines that were selected to
answer this request. Reason only over what is present here.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `answer`: a professional, recruiter-quality response to the message, grounded
  in the tool outputs. Reference concrete figures and findings from the evidence.
- `reasoning_summary`: 1-2 sentences on how you derived the answer and which
  tools mattered.
- `evidence_sources`: the engines/tools you relied on.
- `confidence_note`: your confidence, and any explicit uncertainty when evidence
  is thin or conflicting.

If no tools were run (a general question), answer helpfully from recruiting best
practice, and say so in the confidence note. Return only the JSON object.
