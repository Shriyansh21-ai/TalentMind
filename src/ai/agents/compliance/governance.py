"""Governance scenario simulation + report scaffolding (Modules 8, 9).

Owns the Module 9 scenario simulations (governance impact of hiring without a
committee / interview / executive approval / with missing documentation / with
compensation exceptions) and the ordered section registry for the Module 8
executive compliance report. Pure synthesis — no engine recomputation, no legal
conclusions (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import ComplianceScenario

# Ordered sections of the executive compliance report (Module 8).
REPORT_SECTIONS: list[tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("workflow_status", "Workflow Status"),
    ("governance_status", "Governance Status"),
    ("approval_matrix", "Approval Matrix"),
    ("documentation_review", "Documentation Review"),
    ("audit_findings", "Audit Findings"),
    ("policy_findings", "Policy Findings"),
    ("required_actions", "Required Actions"),
]


def section_titles() -> list[str]:
    """Return the ordered compliance-report section titles."""
    return [title for _key, title in REPORT_SECTIONS]


# Fixed governance-impact scenarios (Module 9). Deterministic, offline.
_SCENARIOS = [
    ComplianceScenario(
        name="Hiring without committee",
        governance_impact="Removes the independent, evidence-weighted decision control; weakens defensibility of the hire.",
        affected_controls=["Committee decision", "Audit: agent participation"],
        severity="High",
    ),
    ComplianceScenario(
        name="Hiring without interview",
        governance_impact="No structured capability evidence; the decision rests on resume/JD signals alone.",
        affected_controls=["Interview completion", "Evidence chain"],
        severity="High",
    ),
    ComplianceScenario(
        name="Hiring without executive approval",
        governance_impact="Critical/strategic hires bypass executive sponsorship; policy exception requiring review.",
        affected_controls=["Executive approval", "Policy: critical-hire review"],
        severity="Medium",
    ),
    ComplianceScenario(
        name="Hiring with missing documentation",
        governance_impact="Reduces audit readiness; gaps surface in an audit or dispute.",
        affected_controls=["Documentation completeness", "Audit readiness"],
        severity="Medium",
    ),
    ComplianceScenario(
        name="Hiring with compensation exceptions",
        governance_impact="Out-of-band / pay-equity exceptions carried into the offer without documented sign-off.",
        affected_controls=["Compensation governance", "Pay-equity review", "Finance approval"],
        severity="Medium",
    ),
]


def build_scenarios(context: dict[str, Any]) -> list[ComplianceScenario]:
    """Return the governance-impact scenario simulations (Module 9)."""
    return list(_SCENARIOS)
