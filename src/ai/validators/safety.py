"""Safety validation for AI responses (Module 8).

The AI reasoning layer must never fabricate resume facts, invent skills, alter
deterministic scores, or contradict the existing engines — and must state
uncertainty when evidence is thin. This guard enforces the structural guarantees
and surfaces soft warnings for the rest.

Design: structural guarantees (which the schema already makes impossible) are
asserted hard; softer, best-effort checks return warnings rather than failing a
response, so the platform degrades gracefully instead of blocking a useful
analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.ai.core.exceptions import SafetyViolationError
from src.ai.schemas.base import BaseAIResponse

# Words that, if a numeric-looking output field appeared, would indicate the AI
# tried to emit a score. Used to assert the schema stays score-free.
_SCORE_TOKENS = ("score", "rating", "percent", "confidence_value")

_UNCERTAINTY_MARKERS = (
    "uncertain",
    "insufficient",
    "limited evidence",
    "thin evidence",
    "not enough",
    "cannot fully",
    "hard to say",
    "unclear",
    "caveat",
    "low confidence",
)


@dataclass
class SafetyReport:
    """Result of a safety pass.

    Attributes:
        ok: Whether the response passed structural safety.
        warnings: Non-fatal advisories to attach to the result / telemetry.
    """

    ok: bool = True
    warnings: list[str] = field(default_factory=list)


class SafetyGuard:
    """Applies platform safety rules to a validated response."""

    def assert_schema_is_score_free(self, schema_cls: type[BaseAIResponse]) -> None:
        """Fail fast if a response schema exposes a numeric score field.

        This makes "the AI never calculates scores" a structural property of the
        platform rather than a hope.

        Raises:
            SafetyViolationError: If the schema declares a score-like field.
        """
        for field_name in schema_cls.field_names():
            lowered = field_name.lower()
            if any(token in lowered for token in _SCORE_TOKENS):
                raise SafetyViolationError(
                    f"Schema {schema_cls.schema_name()} exposes score-like field "
                    f"{field_name!r}; the AI layer must not emit scores."
                )

    def review(
        self,
        response: BaseAIResponse,
        evidence: dict[str, Any],
    ) -> tuple[BaseAIResponse, SafetyReport]:
        """Run soft safety checks and return ``(response, report)``.

        Checks (all non-fatal):
        * When evidence signals low confidence, the response should acknowledge
          uncertainty somewhere in its confidence reasoning.
        * Listed transferable skills should be traceable to the evidence text
          (best-effort fabrication check).

        Args:
            response: The validated response instance.
            evidence: The evidence dict the response was derived from.

        Returns:
            The (unchanged) response and a :class:`SafetyReport`.
        """
        report = SafetyReport()
        data = response.to_dict()
        evidence_blob = _stringify(evidence).lower()

        # --- uncertainty acknowledgement -----------------------------------
        confidence_hint = _low_confidence(evidence)
        conf_text = str(data.get("confidence_reasoning", "")).lower()
        if confidence_hint and not any(m in conf_text for m in _UNCERTAINTY_MARKERS):
            report.warnings.append(
                "Evidence suggests low confidence but the response did not clearly "
                "state uncertainty."
            )

        # --- soft fabrication check on transferable skills -----------------
        for skill in data.get("transferable_skills", []) or []:
            token = re.sub(r"[^a-z0-9+#. ]", "", str(skill).lower()).strip()
            if token and token not in evidence_blob:
                report.warnings.append(
                    f"Transferable skill '{skill}' is not directly present in the "
                    "evidence; verify it was not inferred beyond the data."
                )

        return response, report


def _stringify(value: Any) -> str:
    """Flatten a nested evidence structure into a single searchable string."""
    parts: list[str] = []
    if isinstance(value, dict):
        for key, sub in value.items():
            parts.append(str(key))
            parts.append(_stringify(sub))
    elif isinstance(value, (list, tuple)):
        for sub in value:
            parts.append(_stringify(sub))
    else:
        parts.append(str(value))
    return " ".join(parts)


def _low_confidence(evidence: dict[str, Any]) -> bool:
    """Best-effort read of whether the evidence implies low confidence."""
    intelligence = evidence.get("intelligence", {}) if isinstance(evidence, dict) else {}
    confidence = intelligence.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 55:
        return True
    risk = evidence.get("risk", {}) if isinstance(evidence, dict) else {}
    return str(risk.get("risk_level", "")).lower() == "high"
