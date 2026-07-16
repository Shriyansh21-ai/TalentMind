"""HRIS provider interfaces (Module 2).

Provider *interfaces* for the major enterprise HRIS / HCM systems. Each is a
declarative :class:`~src.platform.integrations.common.provider.BaseIntegrationProvider`
carrying real metadata and capability declarations — **no API is implemented**.
A production HRIS connector subclasses the matching provider (or replaces it in
the registry) and implements live reads/writes behind the same seam.

HRIS integrations are read-oriented by default (employee, org-unit and
compensation master data flows *into* TalentMind), so most declare inbound,
incremental-sync-capable capabilities.
"""

from __future__ import annotations

from src.platform.integrations.common.models import (
    AuthScheme,
    IntegrationCapabilities,
    IntegrationMetadata,
    ProviderCategory,
    SyncDirection,
)
from src.platform.integrations.common.provider import BaseIntegrationProvider

_HRIS_ENTITIES = ["employee", "organization_unit", "job", "compensation", "time_off"]


def _hris_capabilities(
    *, webhooks: bool = False, write: bool = False, realtime: bool = False
) -> IntegrationCapabilities:
    """Return a standard HRIS capability profile (inbound, incremental sync)."""
    return IntegrationCapabilities(
        supports_read=True,
        supports_write=write,
        supports_full_sync=True,
        supports_incremental_sync=True,
        supports_webhooks=webhooks,
        supports_realtime=realtime,
        supports_bulk=True,
        direction=SyncDirection.INBOUND,
        entities=list(_HRIS_ENTITIES),
        scopes=["employees:read", "org:read", "compensation:read"],
    )


class _HrisProvider(BaseIntegrationProvider):
    """Base for HRIS providers — fixes the category to HRIS."""

    capabilities = _hris_capabilities()


class WorkdayProvider(_HrisProvider):
    key = "workday"
    metadata = IntegrationMetadata(
        display_name="Workday HCM",
        vendor="Workday, Inc.",
        category=ProviderCategory.HRIS,
        description="Workday Human Capital Management — employee, org and compensation master data.",
        website="https://www.workday.com",
        docs_url="https://community.workday.com/api",
        logo_emoji="🟠",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.SERVICE_ACCOUNT],
        tags=["enterprise", "hcm", "fortune500"],
    )
    capabilities = _hris_capabilities(webhooks=True, write=True)


class SuccessFactorsProvider(_HrisProvider):
    key = "sap_successfactors"
    metadata = IntegrationMetadata(
        display_name="SAP SuccessFactors",
        vendor="SAP SE",
        category=ProviderCategory.HRIS,
        description="SAP SuccessFactors Employee Central and talent modules.",
        website="https://www.sap.com/products/hcm.html",
        logo_emoji="🔵",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.BASIC],
        tags=["enterprise", "hcm", "fortune500"],
    )
    capabilities = _hris_capabilities(webhooks=True)


class OracleHcmProvider(_HrisProvider):
    key = "oracle_hcm"
    metadata = IntegrationMetadata(
        display_name="Oracle HCM Cloud",
        vendor="Oracle Corporation",
        category=ProviderCategory.HRIS,
        description="Oracle Fusion Human Capital Management Cloud.",
        website="https://www.oracle.com/human-capital-management/",
        logo_emoji="🔴",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.BASIC],
        tags=["enterprise", "hcm", "fortune500"],
    )


class AdpProvider(_HrisProvider):
    key = "adp"
    metadata = IntegrationMetadata(
        display_name="ADP Workforce Now",
        vendor="ADP, LLC",
        category=ProviderCategory.HRIS,
        description="ADP payroll and workforce management platform.",
        website="https://www.adp.com",
        logo_emoji="🟥",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.SERVICE_ACCOUNT],
        tags=["payroll", "hcm"],
    )


class BambooHrProvider(_HrisProvider):
    key = "bamboohr"
    metadata = IntegrationMetadata(
        display_name="BambooHR",
        vendor="BambooHR LLC",
        category=ProviderCategory.HRIS,
        description="BambooHR HRIS for small and mid-sized businesses.",
        website="https://www.bamboohr.com",
        logo_emoji="🎋",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.OAUTH2],
        tags=["smb", "hris"],
    )
    capabilities = _hris_capabilities(webhooks=True)


class RipplingProvider(_HrisProvider):
    key = "rippling"
    metadata = IntegrationMetadata(
        display_name="Rippling",
        vendor="Rippling People Center, Inc.",
        category=ProviderCategory.HRIS,
        description="Rippling unified workforce (HR, IT and finance) platform.",
        website="https://www.rippling.com",
        logo_emoji="🌊",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.API_KEY],
        tags=["hris", "modern"],
    )
    capabilities = _hris_capabilities(webhooks=True, realtime=True)


class DarwinboxProvider(_HrisProvider):
    key = "darwinbox"
    metadata = IntegrationMetadata(
        display_name="Darwinbox",
        vendor="Darwinbox Digital Solutions",
        category=ProviderCategory.HRIS,
        description="Darwinbox HCM suite popular across APAC enterprises.",
        website="https://darwinbox.com",
        logo_emoji="🦎",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.API_KEY],
        tags=["hcm", "apac"],
    )


class UkgProvider(_HrisProvider):
    key = "ukg"
    metadata = IntegrationMetadata(
        display_name="UKG Pro",
        vendor="UKG Inc.",
        category=ProviderCategory.HRIS,
        description="UKG (Ultimate Kronos Group) Pro HCM and workforce management.",
        website="https://www.ukg.com",
        logo_emoji="🟢",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.BASIC],
        tags=["hcm", "workforce"],
    )


class HiBobProvider(_HrisProvider):
    key = "hibob"
    metadata = IntegrationMetadata(
        display_name="HiBob",
        vendor="Hibob Inc.",
        category=ProviderCategory.HRIS,
        description="HiBob (bob) modern HR platform for mid-market companies.",
        website="https://www.hibob.com",
        logo_emoji="🟣",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.OAUTH2],
        tags=["hris", "modern", "midmarket"],
    )
    capabilities = _hris_capabilities(webhooks=True)


class PersonioProvider(_HrisProvider):
    key = "personio"
    metadata = IntegrationMetadata(
        display_name="Personio",
        vendor="Personio SE & Co. KG",
        category=ProviderCategory.HRIS,
        description="Personio HR software for European SMBs.",
        website="https://www.personio.com",
        logo_emoji="🇪🇺",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.OAUTH2],
        tags=["hris", "europe", "smb"],
    )


class GreenhouseHrisProvider(_HrisProvider):
    key = "greenhouse_hris"
    metadata = IntegrationMetadata(
        display_name="Greenhouse (HRIS sync)",
        vendor="Greenhouse Software, Inc.",
        category=ProviderCategory.HRIS,
        description="Greenhouse onboarding / employee data sync surface.",
        website="https://www.greenhouse.io",
        logo_emoji="🌱",
        auth_schemes=[AuthScheme.API_KEY],
        tags=["hris", "onboarding"],
    )


class AshbyHrisProvider(_HrisProvider):
    key = "ashby_hris"
    metadata = IntegrationMetadata(
        display_name="Ashby (HRIS sync)",
        vendor="Ashby, Inc.",
        category=ProviderCategory.HRIS,
        description="Ashby employee and offer data sync surface.",
        website="https://www.ashbyhq.com",
        logo_emoji="🔷",
        auth_schemes=[AuthScheme.API_KEY],
        tags=["hris", "modern"],
    )


def all_providers() -> list[BaseIntegrationProvider]:
    """Return one instance of every built-in HRIS provider interface."""
    return [
        WorkdayProvider(),
        SuccessFactorsProvider(),
        OracleHcmProvider(),
        AdpProvider(),
        BambooHrProvider(),
        RipplingProvider(),
        DarwinboxProvider(),
        UkgProvider(),
        HiBobProvider(),
        PersonioProvider(),
        GreenhouseHrisProvider(),
        AshbyHrisProvider(),
    ]
