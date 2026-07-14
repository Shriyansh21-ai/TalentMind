"""Base class for all AI response schemas.

Every agent's output is a Pydantic model deriving from :class:`BaseAIResponse`.
Centralizing here gives the platform a uniform way to (a) name a schema (used in
the cache key and the deterministic-composer registry), (b) expose a JSON schema
to embed in prompts, and (c) enumerate expected fields for validation/rendering.
No raw provider output ever bypasses one of these models.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class BaseAIResponse(BaseModel):
    """Common behaviour for structured AI responses."""

    model_config = {"extra": "ignore"}

    @classmethod
    def schema_name(cls) -> str:
        """Stable schema identifier (defaults to the class name)."""
        return cls.__name__

    @classmethod
    def field_names(cls) -> List[str]:
        """Return the declared field names in declaration order."""
        return list(cls.model_fields.keys())

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """Return the JSON schema for embedding in prompts / validation."""
        return cls.model_json_schema()

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict of the validated response."""
        return self.model_dump()
