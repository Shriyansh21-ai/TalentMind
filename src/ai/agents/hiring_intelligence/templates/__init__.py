"""Workforce-intelligence configuration (Modules 5, 9, 13).

Pure configuration (no engine / UI import) shared across the analytics modules:

* :data:`KPI_DEFS` — the executive KPIs (Module 5), each with the register it can
  be computed at and a description. KPIs are evidence-backed; those that need event
  history are reported Unavailable without a data provider.
* :data:`OPTIMIZATION_CATALOG` — candidate process/governance improvements
  (Module 9), each with default impact/effort; activated only by observed cohort
  conditions.
* :data:`WORKFORCE_PROVIDERS` — the *names* of the external analytics systems the
  provider interface is designed for (Module 13). No integration is implemented.
* :data:`ANALYTICS_COHORT` — the default bounded cohort size the workspace analyzes
  (org-wide event data is not persisted, so analytics run over a bounded cohort).

Adding a KPI, optimization or future provider is a one-entry data change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# Analytics run over a bounded cohort (the platform stores no org-wide hiring event
# log; see Module 15 — unavailable metrics are marked honestly).
ANALYTICS_COHORT = 25


@dataclass(frozen=True)
class KPIDef:
    """An executive KPI definition (Module 5)."""

    key: str
    name: str
    description: str
    cohort_derivable: bool  # True if computable from the analyzed cohort's intelligence


KPI_DEFS: List[KPIDef] = [
    KPIDef("hiring_health", "Hiring Health Index", "Overall hiring health from the cohort's recommendation + risk mix.", True),
    KPIDef("interview_readiness", "Interview Readiness", "Share of the cohort with a structured interview signal.", True),
    KPIDef("strategic_readiness", "Strategic Hiring Readiness", "Share of strong-hire / high-capability candidates.", True),
    KPIDef("governance_health", "Governance Health", "Maturity of governance controls across the cohort.", False),
    KPIDef("transparency_health", "Transparency Health", "Availability of audit/provenance trails.", False),
    KPIDef("compliance_readiness", "Compliance Readiness", "Share of hires passing compliance controls.", False),
    KPIDef("audit_readiness", "Audit Readiness", "Share of decisions fully reconstructable.", False),
]


@dataclass(frozen=True)
class OptimizationDef:
    """A candidate optimization/improvement (Module 9)."""

    key: str
    area: str
    recommendation: str
    impact: str  # High | Medium | Low
    effort: str  # High | Medium | Low
    trigger: str  # condition token the engine understands


OPTIMIZATION_CATALOG: List[OptimizationDef] = [
    OptimizationDef("connect_warehouse", "Analytics", "Connect an HR data warehouse / people-analytics source to unlock trends, delays and team analytics.", "High", "Medium", "no_provider"),
    OptimizationDef("high_risk_share", "Process", "Strengthen risk-validation in interviews — a material share of the cohort is high-risk.", "High", "Low", "high_risk_share"),
    OptimizationDef("low_interview_ready", "Interview", "Standardize interview planning — many candidates lack a structured interview signal.", "Medium", "Low", "low_interview_ready"),
    OptimizationDef("governance_gaps", "Governance", "Connect approval/document systems to verify governance completeness.", "High", "Medium", "governance_unavailable"),
    OptimizationDef("transparency_gaps", "Transparency", "Enable the audit archive so decisions are fully reconstructable.", "Medium", "Medium", "audit_unavailable"),
    OptimizationDef("weak_recommendations", "Quality", "Review sourcing quality — the cohort skews toward weak/hold recommendations.", "Medium", "Medium", "weak_recommendation_share"),
]

# Module 13 — extension-point registry. Systems the provider interface is DESIGNED
# for; none is implemented.
WORKFORCE_PROVIDERS: List[str] = [
    "HR Data Warehouse",
    "People Analytics",
    "Enterprise BI",
    "Snowflake",
    "BigQuery",
    "Databricks",
    "Azure Synapse",
    "Power BI",
    "Tableau",
]
