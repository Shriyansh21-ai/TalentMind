"""Filesystem-backed AI response cache.

Each entry is a small JSON file named by its cache key. Reads never raise (a
corrupt/missing entry is a miss), so the cache can never break a request.
"""

from __future__ import annotations

import json
import os
from typing import Any

from src.ai.cache.base import BaseCache


class FileCache(BaseCache):
    """A simple, dependency-free JSON file cache."""

    def __init__(self, directory: str = "data/ai_cache") -> None:
        """Bind the cache to ``directory`` (created lazily on first write)."""
        self.directory = directory

    def _path(self, key: str) -> str:
        safe = "".join(c for c in key if c.isalnum() or c in (".", "_", "-"))
        return os.path.join(self.directory, f"{safe}.json")

    def get(self, key: str) -> dict[str, Any] | None:
        """Return the cached payload for ``key`` (``None`` on miss / corruption)."""
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Persist ``value`` under ``key`` via write-then-replace."""
        os.makedirs(self.directory, exist_ok=True)
        path = self._path(key)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def delete(self, key: str) -> None:
        """Remove ``key`` if present."""
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)

    def clear(self) -> None:
        """Remove every cache entry in the directory."""
        if not os.path.isdir(self.directory):
            return
        for filename in os.listdir(self.directory):
            if filename.endswith(".json"):
                os.remove(os.path.join(self.directory, filename))
