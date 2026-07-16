"""Compliance models (Module 8).

Compliance standards, their controls, the evidence collected against them, and
the assessment reports / gap analyses produced. Deterministic and offline — this
is a compliance *framework*, not legal advice, and ships representative control
catalogues rather than the full text of each standard.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity


class ComplianceStandard(str, Enum):
    """A supported compliance standard / framework."""

    GDPR = "gdpr"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    AI_GOVERNANCE = "ai_governance"


class ControlStatus(str, Enum):
    """The assessed state of a control."""

    SATISFIED = "satisfied"
    PARTIAL = "partial"
    UNSATISFIED = "unsatisfied"
    NOT_APPLICABLE = "not_applicable"


class ComplianceControl(PlatformModel):
    """A single control within a standard."""

    code: str
    title: str
    description: str = ""
    status: ControlStatus = ControlStatus.UNSATISFIED
    evidence_count: int = 0


class Evidence(TenantScopedEntity):
    """A piece of evidence collected against a control."""

    standard: ComplianceStandard
    control_code: str
    description: str = ""
    source: str = ""
    reference: str = ""
    collected_at: datetime | None = None


class ComplianceReport(PlatformModel):
    """An assessment of a tenant against a standard."""

    standard: ComplianceStandard
    total_controls: int = 0
    satisfied: int = 0
    partial: int = 0
    unsatisfied: int = 0
    controls: list[ComplianceControl] = Field(default_factory=list)

    @property
    def coverage(self) -> float:
        """Return the fraction of controls satisfied (0..1)."""
        if self.total_controls == 0:
            return 0.0
        return self.satisfied / self.total_controls


class GapAnalysis(PlatformModel):
    """The set of unmet controls for a standard, with recommendations."""

    standard: ComplianceStandard
    gaps: list[ComplianceControl] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @property
    def gap_count(self) -> int:
        """Return the number of controls still to satisfy."""
        return len(self.gaps)
