"""Robust JSON extraction/parsing helpers for provider output.

LLMs frequently wrap JSON in prose or markdown fences. These helpers recover the
JSON object as forgivingly as possible before strict schema validation happens
elsewhere.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from src.ai.core.exceptions import JSONParseError

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_object(text: str) -> str:
    """Return the most likely JSON-object substring from ``text``.

    Tries, in order: a fenced ```json block, then the first balanced ``{...}``
    span. Falls back to the stripped text.

    Args:
        text: Raw model output.

    Returns:
        A candidate JSON string (not guaranteed valid — parse separately).
    """
    if not text:
        return ""

    fence = _FENCE_RE.search(text)
    if fence:
        candidate = fence.group(1).strip()
        if candidate:
            return candidate

    start = text.find("{")
    if start == -1:
        return text.strip()

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:].strip()


def parse_json_object(text: str) -> Dict[str, Any]:
    """Parse ``text`` into a JSON object, tolerating fences / surrounding prose.

    Raises:
        JSONParseError: If no valid JSON object can be recovered.
    """
    candidate = extract_json_object(text)
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError) as exc:
        raise JSONParseError(f"Could not parse JSON from provider output: {exc}") from exc
    if not isinstance(parsed, dict):
        raise JSONParseError("Provider output parsed to a non-object JSON value.")
    return parsed
