"""Structured output schema for the RecruiterCopilotAgent.

Score-free by design: the copilot narrates over tool outputs but never emits a
numeric score of its own.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse


class CopilotResponse(BaseAIResponse):
    """A recruiter-quality answer grounded in structured tool outputs.

    Attributes:
        answer: The professional, evidence-based narrative answer.
        reasoning_summary: Short explanation of how the answer was derived.
        evidence_sources: The deterministic engines/tools cited.
        confidence_note: Confidence / uncertainty statement.
    """

    answer: str
    reasoning_summary: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    confidence_note: str = ""

    @field_validator("answer")
    @classmethod
    def _answer_non_empty(cls, value: str) -> str:
        """Ensure the answer is a non-empty string."""
        text = (value or "").strip()
        if not text:
            raise ValueError("answer must not be empty")
        return text
