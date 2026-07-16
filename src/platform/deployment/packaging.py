"""Packaging & installation (Module 13).

Platform metadata, package information, installation validation and dependency
verification for distributing TalentMind as an enterprise platform. Offline by
default — dependency presence is probed with :func:`importlib.util.find_spec`
(no heavy import executed), so validation is fast and side-effect free.
"""

from __future__ import annotations

import importlib.util

from pydantic import Field

from src.platform.common.models import PlatformModel

#: Runtime dependencies TalentMind requires to boot (import names).
CORE_DEPENDENCIES = ["pydantic", "streamlit", "pandas", "numpy"]
#: Optional dependencies that enable richer features but are not required.
OPTIONAL_DEPENDENCIES = ["torch", "faiss", "sentence_transformers", "plotly", "sklearn"]


class PackageInfo(PlatformModel):
    """Static package metadata for the distributable platform."""

    name: str = "talentmind"
    version: str = "1.0.0"
    edition: str = "Enterprise Edition"
    description: str = "Enterprise Candidate Intelligence Platform"
    python_requires: str = ">=3.11"
    entry_point: str = "streamlit run app.py"
    license: str = "MIT"
    homepage: str = "https://github.com/your-org/talentmind"


class DependencyStatus(PlatformModel):
    """The availability of a single dependency."""

    name: str
    present: bool
    required: bool


class InstallationReport(PlatformModel):
    """The result of validating an installation."""

    package: PackageInfo = Field(default_factory=PackageInfo)
    dependencies: list[DependencyStatus] = Field(default_factory=list)

    @property
    def missing_required(self) -> list[str]:
        """Return required dependencies that are not installed."""
        return [d.name for d in self.dependencies if d.required and not d.present]

    @property
    def valid(self) -> bool:
        """Return whether every required dependency is installed."""
        return not self.missing_required

    @property
    def offline_capable(self) -> bool:
        """Return whether the core (offline) platform can run.

        TalentMind's platform layer needs only the required dependencies; the
        optional ML stack enriches features but is not needed to boot offline.
        """
        return self.valid


def _present(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def package_info() -> PackageInfo:
    """Return the static platform package metadata."""
    return PackageInfo()


def verify_installation() -> InstallationReport:
    """Verify required and optional dependencies are available."""
    deps = [
        DependencyStatus(name=name, present=_present(name), required=True)
        for name in CORE_DEPENDENCIES
    ] + [
        DependencyStatus(name=name, present=_present(name), required=False)
        for name in OPTIONAL_DEPENDENCIES
    ]
    return InstallationReport(package=package_info(), dependencies=deps)


def offline_install_notes() -> str:
    """Return concise offline / air-gapped installation guidance."""
    return (
        "Offline installation:\n"
        "  1. On a connected host: pip download -r requirements.txt -d ./wheels\n"
        "  2. Transfer ./wheels to the air-gapped host.\n"
        "  3. pip install --no-index --find-links ./wheels -r requirements.txt\n"
        "  4. TALENTMIND_ENV=offline_enterprise streamlit run app.py\n"
        "TalentMind's platform layer is offline by default and makes no network "
        "calls; only the optional ML model downloads require connectivity."
    )
