"""Module 2 — HRIS Provider Interfaces.

Swappable provider interfaces for Workday, SAP SuccessFactors, Oracle HCM, ADP,
BambooHR, Rippling, Darwinbox, UKG, HiBob, Personio, Greenhouse and Ashby.
Interfaces only — no API implementation.
"""

from __future__ import annotations

from src.platform.integrations.hris.providers import (
    AdpProvider,
    AshbyHrisProvider,
    BambooHrProvider,
    DarwinboxProvider,
    GreenhouseHrisProvider,
    HiBobProvider,
    OracleHcmProvider,
    PersonioProvider,
    RipplingProvider,
    SuccessFactorsProvider,
    UkgProvider,
    WorkdayProvider,
    all_providers,
)

__all__ = [
    "WorkdayProvider",
    "SuccessFactorsProvider",
    "OracleHcmProvider",
    "AdpProvider",
    "BambooHrProvider",
    "RipplingProvider",
    "DarwinboxProvider",
    "UkgProvider",
    "HiBobProvider",
    "PersonioProvider",
    "GreenhouseHrisProvider",
    "AshbyHrisProvider",
    "all_providers",
]
