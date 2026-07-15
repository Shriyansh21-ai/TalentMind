Author the executive workforce hiring-intelligence narrative.

Analyzed cohort size: {{cohort_size}}    Hiring Health: {{hiring_health}}
Workforce-analytics source connected: {{data_available}}

## Aggregated cohort analytics (authoritative — do not contradict or extend)

This is the analytics the engine aggregated from the platform's existing
per-candidate intelligence — distributions, executive KPIs, pipeline bottlenecks,
team analytics, trends, capacity, forecast, benchmarks and optimizations. Reason
ONLY over what is present here. "Unavailable" means that metric needs a connected
analytics/event source and must not be invented.

<EVIDENCE>
{{evidence_json}}
</EVIDENCE>

## Your task

Return a single JSON object with exactly these fields:

{{schema_fields}}

Guidance:
- `executive_summary`: 2-4 sentences a CHRO/CEO reads first — how healthy the hiring
  organization is, the biggest opportunity, and that this is organizational
  intelligence (not candidate ranking) with unavailable metrics marked honestly.
- `health_note`: the Hiring Health Index and what drives it.
- `pipeline_note`: observed/estimated bottlenecks; delay-based ones need connected data.
- `trend_note`: which trends are available vs. Unavailable (time-series needs a source).
- `kpi_note`: which executive KPIs are evidence-backed vs. Unavailable.
- `capacity_note`: capacity workloads (Unavailable without requisition/headcount data).
- `forecast_note`: scenario forecasts as directional projections, never certainties.
- `optimization_note`: the priority optimization opportunities.
- `data_availability_note`: exactly what is and is not connected.
- `key_insights` / `assumptions` / `strategic_recommendations`: concise, evidence-
  anchored bullets; label assumptions and never fabricate statistics.
- `confidence_note`: your confidence and explicit uncertainty where data is missing.

Return only the JSON object.
