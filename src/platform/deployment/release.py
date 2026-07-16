"""Release engineering (Module 7).

Semantic versioning, release manifests, build/artifact metadata, version
history, a release-notes generator, a compatibility matrix, a migration tracker
and a deprecation registry. Deterministic and offline.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.models import Entity, PlatformModel
from src.platform.deployment.common.errors import ReleaseError

_SEMVER = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


class SemanticVersion(PlatformModel):
    """A parsed semantic version supporting comparison."""

    major: int = 1
    minor: int = 0
    patch: int = 0
    prerelease: str = ""
    build: str = ""

    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        """Parse a ``MAJOR.MINOR.PATCH[-pre][+build]`` string."""
        match = _SEMVER.match(value.strip())
        if not match:
            raise ReleaseError(f"invalid semantic version '{value}'")
        g = match.groupdict()
        return cls(
            major=int(g["major"]), minor=int(g["minor"]), patch=int(g["patch"]),
            prerelease=g["prerelease"] or "", build=g["build"] or "",
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        if self.build:
            base += f"+{self.build}"
        return base

    @property
    def core(self) -> tuple[int, int, int]:
        """Return the (major, minor, patch) core triple."""
        return (self.major, self.minor, self.patch)

    def is_newer_than(self, other: "SemanticVersion") -> bool:
        """Return whether this version's core is newer than ``other``'s.

        A release (no prerelease) outranks a prerelease of the same core.
        """
        if self.core != other.core:
            return self.core > other.core
        if self.prerelease == other.prerelease:
            return False
        if not self.prerelease:
            return True  # release > prerelease
        if not other.prerelease:
            return False
        return self.prerelease > other.prerelease

    def bump_major(self) -> "SemanticVersion":
        return SemanticVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "SemanticVersion":
        return SemanticVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "SemanticVersion":
        return SemanticVersion(major=self.major, minor=self.minor, patch=self.patch + 1)


class BuildMetadata(PlatformModel):
    """Metadata describing how an artifact was built."""

    build_id: str = ""
    git_sha: str = ""
    builder: str = "ci"
    reproducible: bool = True


class ArtifactMetadata(PlatformModel):
    """Metadata describing a released artifact."""

    name: str
    artifact_type: str = "container"  # container / wheel / sdist / bundle
    checksum: str = ""
    size_bytes: int = 0


class ChangeType(str, Enum):
    """The kind of change in a release (drives notes grouping + version bump)."""

    FEATURE = "feature"
    FIX = "fix"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCS = "docs"
    BREAKING = "breaking"


class ChangeEntry(PlatformModel):
    """A single changelog entry."""

    change_type: ChangeType = ChangeType.FEATURE
    summary: str = ""
    reference: str = ""


class ReleaseManifest(Entity):
    """An immutable manifest for one release."""

    version: str
    channel: str = "stable"
    build: BuildMetadata = Field(default_factory=BuildMetadata)
    artifacts: list[ArtifactMetadata] = Field(default_factory=list)
    changes: list[ChangeEntry] = Field(default_factory=list)
    notes: str = ""
    released_at: datetime | None = None


class Deprecation(PlatformModel):
    """A registered deprecation."""

    feature: str
    since_version: str
    remove_in_version: str = ""
    replacement: str = ""


class Migration(PlatformModel):
    """A tracked migration between versions."""

    identifier: str
    from_version: str
    to_version: str
    description: str = ""
    applied: bool = False


class ReleaseManager:
    """Manage releases, version history, notes, compatibility and migrations."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._releases: list[ReleaseManifest] = []
        self._deprecations: list[Deprecation] = []
        self._migrations: list[Migration] = []
        # Minimum client/plugin version compatible with a given platform version.
        self._compatibility: dict[str, str] = {}

    # -- releases -----------------------------------------------------------

    def register_release(
        self,
        version: str,
        *,
        channel: str = "stable",
        build: BuildMetadata | None = None,
        artifacts: list[ArtifactMetadata] | None = None,
        changes: list[ChangeEntry] | None = None,
    ) -> ReleaseManifest:
        """Register a release manifest (version must be valid semver)."""
        SemanticVersion.parse(version)  # validates
        now = self._clock.now()
        manifest = ReleaseManifest(
            id=generate_id("rel"), version=version, channel=channel,
            build=build or BuildMetadata(), artifacts=artifacts or [],
            changes=changes or [], notes=self.generate_release_notes(version, changes or []),
            released_at=now, created_at=now, updated_at=now,
        )
        self._releases.append(manifest)
        return manifest

    def version_history(self) -> list[str]:
        """Return released versions, newest first."""
        versions = [SemanticVersion.parse(r.version) for r in self._releases]
        versions.sort(key=lambda v: (v.core, v.prerelease or "~"), reverse=True)
        return [str(v) for v in versions]

    def latest(self) -> str | None:
        """Return the newest released version (or ``None``)."""
        history = self.version_history()
        return history[0] if history else None

    def generate_release_notes(self, version: str, changes: list[ChangeEntry]) -> str:
        """Render Markdown release notes grouped by change type."""
        lines = [f"# Release {version}", ""]
        groups: dict[ChangeType, list[ChangeEntry]] = {}
        for change in changes:
            groups.setdefault(change.change_type, []).append(change)
        headings = {
            ChangeType.BREAKING: "⚠️ Breaking Changes",
            ChangeType.FEATURE: "✨ Features",
            ChangeType.FIX: "🐛 Fixes",
            ChangeType.PERFORMANCE: "⚡ Performance",
            ChangeType.SECURITY: "🔒 Security",
            ChangeType.DOCS: "📝 Documentation",
        }
        for change_type, heading in headings.items():
            entries = groups.get(change_type, [])
            if not entries:
                continue
            lines.append(f"## {heading}")
            for entry in entries:
                ref = f" ({entry.reference})" if entry.reference else ""
                lines.append(f"- {entry.summary}{ref}")
            lines.append("")
        if not changes:
            lines.append("_No changes recorded._")
        return "\n".join(lines).strip()

    def suggest_bump(self, current: str, changes: list[ChangeEntry]) -> str:
        """Suggest the next version from the changes (semver rules)."""
        version = SemanticVersion.parse(current)
        types = {c.change_type for c in changes}
        if ChangeType.BREAKING in types:
            return str(version.bump_major())
        if ChangeType.FEATURE in types:
            return str(version.bump_minor())
        return str(version.bump_patch())

    # -- compatibility / migrations / deprecations -------------------------

    def set_compatibility(self, platform_version: str, min_client_version: str) -> None:
        """Record the minimum compatible client version for a platform version."""
        self._compatibility[platform_version] = min_client_version

    def compatibility_matrix(self) -> dict[str, str]:
        """Return the platform→min-client compatibility matrix."""
        return dict(self._compatibility)

    def is_compatible(self, platform_version: str, client_version: str) -> bool:
        """Return whether ``client_version`` satisfies the platform's minimum."""
        minimum = self._compatibility.get(platform_version)
        if minimum is None:
            return True
        client = SemanticVersion.parse(client_version)
        floor = SemanticVersion.parse(minimum)
        return client.core >= floor.core

    def track_migration(
        self, identifier: str, from_version: str, to_version: str, *, description: str = ""
    ) -> Migration:
        """Register a migration between versions."""
        migration = Migration(
            identifier=identifier, from_version=from_version,
            to_version=to_version, description=description,
        )
        self._migrations.append(migration)
        return migration

    def apply_migration(self, identifier: str) -> Migration:
        """Mark a migration applied."""
        for migration in self._migrations:
            if migration.identifier == identifier:
                migration.applied = True
                return migration
        raise ReleaseError(f"unknown migration '{identifier}'")

    def pending_migrations(self) -> list[Migration]:
        """Return migrations not yet applied."""
        return [m for m in self._migrations if not m.applied]

    def deprecate(
        self, feature: str, since_version: str, *, remove_in_version: str = "",
        replacement: str = "",
    ) -> Deprecation:
        """Register a deprecation."""
        deprecation = Deprecation(
            feature=feature, since_version=since_version,
            remove_in_version=remove_in_version, replacement=replacement,
        )
        self._deprecations.append(deprecation)
        return deprecation

    def deprecations(self) -> list[Deprecation]:
        """Return the deprecation registry."""
        return list(self._deprecations)
