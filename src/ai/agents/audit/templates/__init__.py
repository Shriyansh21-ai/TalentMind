"""Audit & explainability configuration (Modules 1, 2, 12).

Pure configuration (no engine / UI import) shared across the audit modules:

* :data:`AGENT_CATALOG` — the ordered catalog of the agents/engines that can
  participate in a hiring decision, each with the evidence-source label it reports
  under, the evidence type it produces, its stage order and the modules it feeds
  (Modules 1, 2). The labels match exactly what the upstream engines emit, so
  participation is *derived*, never fabricated.
* :data:`AUDIT_ARCHIVE_PROVIDERS` — the *names* of the external audit/archive
  systems the provider interface is designed for (Module 12). No connector is
  implemented — an extension-point registry only.

Adding an agent to the catalog or a future archive provider is a one-entry change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class AgentCatalogEntry:
    """One agent/engine that can participate in a hiring decision (Modules 1, 2).

    Attributes:
        source: The evidence-source label the engine emits (matched against the
            observed evidence sources — must be exact).
        stage: Human-readable decision-journey stage name.
        evidence_type: The kind of evidence this agent produces.
        origin_agent: The agent/engine that owns the evidence.
        order: Chronological order in the decision journey.
        feeds: Downstream stages this agent's output feeds (for the evidence graph).
    """

    source: str
    stage: str
    evidence_type: str
    origin_agent: str
    order: int
    feeds: list[str] = field(default_factory=list)


# Ordered catalog. ``source`` labels match the exact strings the engines report
# (see committee.gather_evidence._sources and the downstream agents).
AGENT_CATALOG: list[AgentCatalogEntry] = [
    AgentCatalogEntry(
        "Resume Analyst Agent",
        "Resume analysis",
        "Resume quality analysis",
        "Resume Analyst Agent",
        1,
        ["Candidate Intelligence engine", "AI Hiring Committee"],
    ),
    AgentCatalogEntry(
        "JD Analyst Agent",
        "JD analysis",
        "Job-description analysis",
        "JD Analyst Agent",
        2,
        ["AI Hiring Committee", "Compensation Governance Agent"],
    ),
    AgentCatalogEntry(
        "Candidate Intelligence engine",
        "Candidate intelligence",
        "Candidate capability signals",
        "Candidate Intelligence engine",
        3,
        ["AI Hiring Committee", "Compensation Governance Agent"],
    ),
    AgentCatalogEntry(
        "Career Timeline Intelligence",
        "Career timeline",
        "Career trajectory",
        "Career Timeline Intelligence",
        4,
        ["AI Hiring Committee", "Pay Equity Guardian"],
    ),
    AgentCatalogEntry(
        "Resume Risk Detection",
        "Risk analysis",
        "Risk findings",
        "Resume Risk Detection",
        5,
        ["AI Hiring Committee", "Hiring Compliance"],
    ),
    AgentCatalogEntry(
        "Hiring Recommendation engine",
        "Hiring recommendation",
        "Recommendation",
        "Hiring Recommendation engine",
        6,
        ["AI Hiring Committee"],
    ),
    AgentCatalogEntry(
        "Interview Intelligence",
        "Interview plan",
        "Interview plan",
        "Interview Intelligence",
        7,
        ["AI Hiring Committee"],
    ),
    AgentCatalogEntry(
        "AI Hiring Committee",
        "Committee decision",
        "Consensus hiring decision",
        "AI Hiring Committee",
        8,
        ["Compensation Governance Agent", "Hiring Compliance"],
    ),
    AgentCatalogEntry(
        "Compensation Governance Agent",
        "Compensation review",
        "Compensation recommendation",
        "Compensation Governance Agent",
        9,
        ["Pay Equity Guardian"],
    ),
    AgentCatalogEntry(
        "Pay Equity Guardian",
        "Pay-equity review",
        "Internal-equity assessment",
        "Pay Equity Guardian",
        10,
        ["Hiring Compliance"],
    ),
    AgentCatalogEntry(
        "Hiring Compliance",
        "Compliance review",
        "Governance compliance status",
        "Hiring Compliance",
        11,
        ["Final Decision"],
    ),
]

CATALOG_BY_SOURCE: dict[str, AgentCatalogEntry] = {e.source: e for e in AGENT_CATALOG}

# The terminal node of the evidence graph / decision journey.
FINAL_DECISION_NODE = "Final Decision"

# Module 12 — extension-point registry. Systems the archive provider interface is
# DESIGNED for; none is implemented.
AUDIT_ARCHIVE_PROVIDERS: list[str] = [
    "SIEM",
    "Document Management System",
    "Compliance Archive",
    "Audit System",
    "Enterprise Data Lake",
]
