"""Evidence graph construction (Modules 2, 10).

Builds a directed evidence graph whose nodes are the participating agents (plus
the final-decision node) and whose edges show which agent's evidence fed which
downstream decision. Node ``present`` and edge ``active`` flags are derived from
the observed evidence sources — the graph reflects what actually happened, never a
fabricated flow.
"""

from __future__ import annotations

from typing import Any, Dict

from src.ai.agents.audit.schemas import EvidenceEdge, EvidenceGraph, EvidenceNode
from src.ai.agents.audit.templates import AGENT_CATALOG, FINAL_DECISION_NODE


def build_evidence_graph(context: Dict[str, Any]) -> EvidenceGraph:
    """Build the evidence graph (Modules 2, 10)."""
    sources = set(context.get("evidence_sources", []))
    committee_present = "AI Hiring Committee" in sources

    nodes = [
        EvidenceNode(id=e.source, label=e.stage, kind="agent", present=e.source in sources)
        for e in AGENT_CATALOG
    ]
    nodes.append(
        EvidenceNode(id=FINAL_DECISION_NODE, label="Final Decision", kind="decision", present=committee_present)
    )
    present_ids = {n.id for n in nodes if n.present}

    edges = []
    for entry in AGENT_CATALOG:
        for target in entry.feeds:
            edges.append(
                EvidenceEdge(
                    source=entry.source,
                    target=target,
                    active=(entry.source in present_ids and target in present_ids),
                )
            )
    return EvidenceGraph(nodes=nodes, edges=edges)
