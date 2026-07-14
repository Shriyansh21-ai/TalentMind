"""Prompt management: versioned, file-based templates.

Prompts are **never** hard-coded in Python. They live as ``{name}.{version}.md``
files under ``src/ai/prompts/templates/`` and are loaded, cached, validated and
rendered here. Placeholders use ``{{double_brace}}`` syntax. Every agent reuses
this loader, so adding a prompt is a matter of dropping a file in the folder.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Set

from src.ai.core.exceptions import PromptNotFoundError, PromptRenderError

_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


@dataclass
class PromptTemplate:
    """A single, versioned prompt template.

    Attributes:
        name: Template name (file stem before the version).
        version: Template version string (e.g. ``"v1"``).
        text: Raw template text.
        placeholders: Placeholder names discovered in the text.
    """

    name: str
    version: str
    text: str
    placeholders: Set[str] = field(default_factory=set)

    def render(self, **values: object) -> str:
        """Render the template, substituting every ``{{placeholder}}``.

        Args:
            **values: Placeholder values.

        Returns:
            The rendered prompt string.

        Raises:
            PromptRenderError: If any placeholder in the template has no value.
        """
        missing = self.placeholders - set(values.keys())
        if missing:
            raise PromptRenderError(
                f"Missing placeholder(s) for prompt {self.name}.{self.version}: "
                f"{sorted(missing)}"
            )

        def _replace(match: "re.Match[str]") -> str:
            return str(values[match.group(1)])

        return _PLACEHOLDER_RE.sub(_replace, self.text)


class PromptLoader:
    """Loads and caches :class:`PromptTemplate` objects from a directory."""

    def __init__(self, templates_dir: str = _TEMPLATES_DIR) -> None:
        """Bind the loader to ``templates_dir``."""
        self.templates_dir = templates_dir

    def _path(self, name: str, version: str) -> str:
        return os.path.join(self.templates_dir, f"{name}.{version}.md")

    def load(self, name: str, version: str = "v1") -> PromptTemplate:
        """Load a template by ``name`` and ``version``.

        Raises:
            PromptNotFoundError: If the template file does not exist.
        """
        path = self._path(name, version)
        if not os.path.exists(path):
            raise PromptNotFoundError(
                f"Prompt template not found: {name}.{version} (looked in {path})"
            )
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        placeholders = set(_PLACEHOLDER_RE.findall(text))
        return PromptTemplate(
            name=name, version=version, text=text, placeholders=placeholders
        )

    def render(self, name: str, version: str = "v1", **values: object) -> str:
        """Convenience: load ``name.version`` and render it with ``values``."""
        return self.load(name, version).render(**values)

    def list_versions(self, name: str) -> List[str]:
        """Return the available versions of ``name`` (sorted)."""
        if not os.path.isdir(self.templates_dir):
            return []
        versions: List[str] = []
        prefix = f"{name}."
        for filename in os.listdir(self.templates_dir):
            if filename.startswith(prefix) and filename.endswith(".md"):
                middle = filename[len(prefix) : -len(".md")]
                if middle:
                    versions.append(middle)
        return sorted(versions)

    def available(self) -> Dict[str, List[str]]:
        """Return ``{name: [versions]}`` for every template on disk."""
        result: Dict[str, List[str]] = {}
        if not os.path.isdir(self.templates_dir):
            return result
        for filename in os.listdir(self.templates_dir):
            if not filename.endswith(".md"):
                continue
            stem = filename[: -len(".md")]
            if "." not in stem:
                continue
            name, version = stem.rsplit(".", 1)
            result.setdefault(name, []).append(version)
        for name in result:
            result[name].sort()
        return result


@lru_cache(maxsize=1)
def get_default_loader() -> PromptLoader:
    """Return a process-wide default :class:`PromptLoader` (cached)."""
    return PromptLoader()
