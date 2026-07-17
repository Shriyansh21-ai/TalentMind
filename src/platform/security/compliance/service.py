"""Compliance service (Module 8).

Ships representative control catalogues for GDPR, SOC 2, ISO 27001, HIPAA,
PCI-DSS and AI-governance readiness, collects tenant evidence against those
controls, assesses coverage, and produces compliance reports + gap analyses.
Tenant-isolated and clock-driven. Framework only — no legal advice.
"""

from __future__ import annotations

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.security.compliance.models import (
    ComplianceControl,
    ComplianceReport,
    ComplianceStandard,
    ControlStatus,
    Evidence,
    GapAnalysis,
)

# Representative control catalogues (code, title) per standard.
_CATALOGUES: dict[ComplianceStandard, list[tuple[str, str]]] = {
    ComplianceStandard.GDPR: [
        ("GDPR-5", "Lawfulness, fairness and transparency"),
        ("GDPR-15", "Right of access"),
        ("GDPR-17", "Right to erasure"),
        ("GDPR-25", "Data protection by design and by default"),
        ("GDPR-32", "Security of processing"),
        ("GDPR-33", "Breach notification"),
    ],
    ComplianceStandard.SOC2: [
        ("CC6.1", "Logical and physical access controls"),
        ("CC6.6", "Encryption of data"),
        ("CC7.2", "Security monitoring"),
        ("CC7.3", "Incident response"),
        ("CC8.1", "Change management"),
        ("A1.2", "Availability / capacity"),
    ],
    ComplianceStandard.ISO27001: [
        ("A.5", "Information security policies"),
        ("A.8", "Asset management"),
        ("A.9", "Access control"),
        ("A.12", "Operations security"),
        ("A.16", "Incident management"),
        ("A.18", "Compliance"),
    ],
    ComplianceStandard.HIPAA: [
        ("164.308", "Administrative safeguards"),
        ("164.310", "Physical safeguards"),
        ("164.312", "Technical safeguards"),
        ("164.312(a)", "Access control"),
        ("164.312(b)", "Audit controls"),
        ("164.312(e)", "Transmission security"),
    ],
    ComplianceStandard.PCI_DSS: [
        ("PCI-3", "Protect stored cardholder data"),
        ("PCI-4", "Encrypt transmission"),
        ("PCI-7", "Restrict access by need-to-know"),
        ("PCI-8", "Identify and authenticate access"),
        ("PCI-10", "Track and monitor access"),
        ("PCI-12", "Information security policy"),
    ],
    ComplianceStandard.AI_GOVERNANCE: [
        ("AI-1", "Model inventory and documentation"),
        ("AI-2", "Bias and fairness evaluation"),
        ("AI-3", "Human oversight of decisions"),
        ("AI-4", "Explainability and audit trail"),
        ("AI-5", "Data provenance and consent"),
    ],
}


class ComplianceService:
    """Evidence collection, assessment, reporting and gap analysis."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self.evidence: InMemoryRepository[Evidence] = InMemoryRepository("evidence")

    # -- framework ----------------------------------------------------------

    @staticmethod
    def standards() -> list[ComplianceStandard]:
        """Return every supported compliance standard."""
        return list(_CATALOGUES)

    @staticmethod
    def controls(standard: ComplianceStandard) -> list[ComplianceControl]:
        """Return the control catalogue for a standard."""
        return [
            ComplianceControl(code=code, title=title)
            for code, title in _CATALOGUES.get(standard, [])
        ]

    # -- evidence -----------------------------------------------------------

    def collect_evidence(
        self,
        tenant_id: str,
        organization_id: str,
        standard: ComplianceStandard,
        control_code: str,
        *,
        description: str = "",
        source: str = "",
        reference: str = "",
    ) -> Evidence:
        """Record a piece of evidence for a control."""
        now = self._clock.now()
        evidence = Evidence(
            id=generate_id("evi"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            standard=standard,
            control_code=control_code,
            description=description,
            source=source,
            reference=reference,
            collected_at=now,
            created_at=now,
            updated_at=now,
        )
        return self.evidence.add(evidence)

    def evidence_for(self, tenant_id: str, standard: ComplianceStandard) -> list[Evidence]:
        """Return a tenant's evidence for a standard."""
        return self.evidence.list(tenant_id=tenant_id, where=lambda e: e.standard == standard)

    # -- assessment ---------------------------------------------------------

    def assess(self, tenant_id: str, standard: ComplianceStandard) -> ComplianceReport:
        """Assess a tenant against a standard from collected evidence."""
        evidence = self.evidence_for(tenant_id, standard)
        counts: dict[str, int] = {}
        for item in evidence:
            counts[item.control_code] = counts.get(item.control_code, 0) + 1

        controls: list[ComplianceControl] = []
        satisfied = partial = unsatisfied = 0
        for control in self.controls(standard):
            n = counts.get(control.code, 0)
            control.evidence_count = n
            if n >= 2:
                control.status = ControlStatus.SATISFIED
                satisfied += 1
            elif n == 1:
                control.status = ControlStatus.PARTIAL
                partial += 1
            else:
                control.status = ControlStatus.UNSATISFIED
                unsatisfied += 1
            controls.append(control)

        return ComplianceReport(
            standard=standard,
            total_controls=len(controls),
            satisfied=satisfied,
            partial=partial,
            unsatisfied=unsatisfied,
            controls=controls,
        )

    def gap_analysis(self, tenant_id: str, standard: ComplianceStandard) -> GapAnalysis:
        """Return the unmet controls for a standard, with recommendations."""
        report = self.assess(tenant_id, standard)
        gaps = [
            c
            for c in report.controls
            if c.status in (ControlStatus.UNSATISFIED, ControlStatus.PARTIAL)
        ]
        recommendations = [f"Provide evidence for {c.code} — {c.title}" for c in gaps]
        return GapAnalysis(standard=standard, gaps=gaps, recommendations=recommendations)
