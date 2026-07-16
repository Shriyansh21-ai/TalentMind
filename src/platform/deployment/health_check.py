"""Repository health check (Module 16).

A deterministic, offline repository audit focused on the additive
``src/platform`` layer: it imports every platform submodule to catch broken or
circular imports, enforces the additive architecture rule across the Phase-6
sub-platforms, checks package naming, and scans for orphan/temp/debug files.
Produces a :class:`HealthSummary` and a Markdown report. It deliberately does
**not** import the heavy Phase 1-5 ML modules (torch/faiss) — those are covered
by the full test suite.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path

from pydantic import Field

from src.platform.common.models import PlatformModel

# Phase 1-5 business packages the additive platform layers must never import.
_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from|import)\s+src\."
    r"(scoring|semantic|intelligence|hiring|recruiter|pipeline|reasoning|"
    r"ingestion|insights|comparison|talent_pool|interview|filtering|dashboard|"
    r"llm|ai|models)\b",
    re.MULTILINE,
)
_ADDITIVE_DIRS = ["integrations", "runtime", "security", "deployment"]
_ORPHAN_PATTERNS = re.compile(r".*\.(bak|tmp|orig|swp|rej)$|^debug_.*\.py$|^scratch.*")
_PACKAGE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class HealthIssue(PlatformModel):
    """A single repository-health finding."""

    check: str
    detail: str


class HealthSummary(PlatformModel):
    """The aggregated repository-health result."""

    modules_scanned: int = 0
    import_errors: list[HealthIssue] = Field(default_factory=list)
    additive_violations: list[HealthIssue] = Field(default_factory=list)
    naming_issues: list[HealthIssue] = Field(default_factory=list)
    orphan_files: list[HealthIssue] = Field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return (
            len(self.import_errors)
            + len(self.additive_violations)
            + len(self.naming_issues)
            + len(self.orphan_files)
        )

    @property
    def healthy(self) -> bool:
        """Return whether the repository passed every health check."""
        return self.total_issues == 0


class RepositoryHealthCheck:
    """Audits the additive platform layer of the repository."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path(__file__).resolve().parents[3]
        self._platform_dir = self._root / "src" / "platform"

    def run(self) -> HealthSummary:
        """Run every check and return a summary."""
        summary = HealthSummary()
        self._check_imports(summary)
        self._check_additive_rule(summary)
        self._check_naming(summary)
        self._check_orphans(summary)
        return summary

    # -- checks -------------------------------------------------------------

    def _check_imports(self, summary: HealthSummary) -> None:
        """Import every src.platform submodule, catching broken/circular imports."""
        import src.platform as platform_pkg

        scanned = 0
        for module in pkgutil.walk_packages(
            platform_pkg.__path__, prefix="src.platform."
        ):
            name = module.name
            # Demo/UI-free: skip nothing — platform layer is dependency-light.
            try:
                importlib.import_module(name)
                scanned += 1
            except Exception as exc:  # broken or circular import
                summary.import_errors.append(
                    HealthIssue(check="import", detail=f"{name}: {exc}")
                )
        summary.modules_scanned = scanned

    def _check_additive_rule(self, summary: HealthSummary) -> None:
        for sub in _ADDITIVE_DIRS:
            base = self._platform_dir / sub
            if not base.exists():
                continue
            for path in base.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if _FORBIDDEN_IMPORT.search(text):
                    summary.additive_violations.append(
                        HealthIssue(
                            check="additive_rule",
                            detail=str(path.relative_to(self._root)),
                        )
                    )

    def _check_naming(self, summary: HealthSummary) -> None:
        for path in self._platform_dir.rglob("*"):
            if path.is_dir() and path.name != "__pycache__":
                if not _PACKAGE_NAME.match(path.name):
                    summary.naming_issues.append(
                        HealthIssue(
                            check="naming", detail=str(path.relative_to(self._root))
                        )
                    )

    def _check_orphans(self, summary: HealthSummary) -> None:
        for path in self._platform_dir.rglob("*"):
            if path.is_file() and _ORPHAN_PATTERNS.match(path.name):
                summary.orphan_files.append(
                    HealthIssue(
                        check="orphan_file", detail=str(path.relative_to(self._root))
                    )
                )

    # -- reporting ----------------------------------------------------------

    def report_markdown(self, summary: HealthSummary | None = None) -> str:
        """Render the health summary as a Markdown report."""
        s = summary or self.run()
        status = "✅ HEALTHY" if s.healthy else "❌ ISSUES FOUND"
        lines = [
            "# Repository Health Summary",
            "",
            f"**Status:** {status} · **Platform modules scanned:** {s.modules_scanned} · "
            f"**Total issues:** {s.total_issues}",
            "",
            "| Check | Result |",
            "|---|---|",
            f"| Broken / circular imports | {'✅ none' if not s.import_errors else f'❌ {len(s.import_errors)}'} |",
            f"| Additive-rule violations | {'✅ none' if not s.additive_violations else f'❌ {len(s.additive_violations)}'} |",
            f"| Package naming | {'✅ consistent' if not s.naming_issues else f'❌ {len(s.naming_issues)}'} |",
            f"| Orphan / temp / debug files | {'✅ none' if not s.orphan_files else f'❌ {len(s.orphan_files)}'} |",
            "",
        ]
        for title, issues in [
            ("Import errors", s.import_errors),
            ("Additive violations", s.additive_violations),
            ("Naming issues", s.naming_issues),
            ("Orphan files", s.orphan_files),
        ]:
            if issues:
                lines.append(f"### {title}")
                lines.extend(f"- `{i.detail}`" for i in issues)
                lines.append("")
        return "\n".join(lines).strip()
