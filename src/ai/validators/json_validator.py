"""Structured-output validation.

Turns raw provider text into a validated schema instance, or raises a typed error
the runner can act on (retry or fall back). No raw provider output is ever
returned — only a validated model instance.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import ValidationError

from src.ai.core.exceptions import SchemaValidationError
from src.ai.schemas.base import BaseAIResponse
from src.ai.utils.json_utils import parse_json_object

T = TypeVar("T", bound=BaseAIResponse)


def validate_text(text: str, schema_cls: type[T]) -> T:
    """Parse ``text`` as JSON and validate it against ``schema_cls``.

    Args:
        text: Raw provider output (may contain fences / surrounding prose).
        schema_cls: The response schema to validate against.

    Returns:
        A validated schema instance.

    Raises:
        JSONParseError: If no JSON object can be recovered.
        SchemaValidationError: If the JSON does not satisfy the schema.
    """
    payload = parse_json_object(text)
    try:
        return schema_cls(**payload)
    except ValidationError as exc:
        raise SchemaValidationError(
            f"Output failed {schema_cls.schema_name()} validation: {exc}"
        ) from exc
