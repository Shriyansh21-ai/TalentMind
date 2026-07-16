"""Module 3 — ATS Provider Interfaces.

Swappable provider interfaces for Greenhouse, Lever, SmartRecruiters, Ashby,
Workable, JazzHR, iCIMS, Jobvite, Bullhorn and Teamtailor. Provider architecture
only — no API implementation.
"""

from __future__ import annotations

from src.platform.integrations.ats.providers import (
    AshbyProvider,
    BullhornProvider,
    GreenhouseProvider,
    IcimsProvider,
    JazzHrProvider,
    JobviteProvider,
    LeverProvider,
    SmartRecruitersProvider,
    TeamtailorProvider,
    WorkableProvider,
    all_providers,
)

__all__ = [
    "GreenhouseProvider",
    "LeverProvider",
    "SmartRecruitersProvider",
    "AshbyProvider",
    "WorkableProvider",
    "JazzHrProvider",
    "IcimsProvider",
    "JobviteProvider",
    "BullhornProvider",
    "TeamtailorProvider",
    "all_providers",
]
