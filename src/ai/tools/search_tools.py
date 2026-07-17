"""Search / matching tools (wrap FAISS semantic search + skill-gap engine)."""

from __future__ import annotations

from typing import Any

from src.ai.tools.base import (
    BaseTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
    ToolValidationError,
)
from src.models.candidates import Candidate
from src.scoring.skill_gap import get_skill_gap


def _candidate_row(candidate: Candidate, score: float) -> dict[str, Any]:
    """Project a candidate + score into a compact result row."""
    return {
        "candidate_id": candidate.candidate_id,
        "title": candidate.profile.current_title,
        "company": candidate.profile.current_company,
        "location": candidate.profile.location,
        "years_of_experience": candidate.profile.years_of_experience,
        "score": round(float(score), 3),
    }


class FAISSSearchTool(BaseTool):
    """Semantic candidate search backed by the FAISS recruiter-search engine."""

    metadata = ToolMetadata(
        name="faiss_search",
        description="Semantically search candidates for a free-text query.",
        input_fields=["query", "top_k"],
        engine="FAISS Recruiter Search",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        if not str(tool_input.get("query", "")).strip():
            raise ToolValidationError("faiss_search requires a non-empty 'query'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        query = str(tool_input["query"]).strip()
        top_k = int(tool_input.get("top_k", 5))
        hits = context.repository.search(query, top_k=top_k)
        rows = [_candidate_row(c, s) for c, s in hits]
        confidence = min(100.0, rows[0]["score"] * 100) if rows else 0.0
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={"query": query, "count": len(rows), "results": rows},
            summary=f"Found {len(rows)} candidate(s) semantically matching the query.",
            evidence_sources=["FAISS semantic search"],
            confidence=confidence,
        )


class CandidateSearchTool(BaseTool):
    """Keyword candidate search over the pool (works without a FAISS index)."""

    metadata = ToolMetadata(
        name="candidate_search",
        description="Keyword search of candidates by title, skills and summary.",
        input_fields=["query", "top_k"],
        engine="Candidate Pool",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        if not str(tool_input.get("query", "")).strip():
            raise ToolValidationError("candidate_search requires a non-empty 'query'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        query = str(tool_input["query"]).strip().lower()
        top_k = int(tool_input.get("top_k", 5))
        tokens = [t for t in query.replace(",", " ").split() if t]

        scored: list[tuple] = []
        for candidate in context.repository.sample(limit=500):
            haystack = " ".join(
                [
                    candidate.profile.current_title,
                    candidate.profile.headline,
                    candidate.profile.summary,
                    " ".join(s.name for s in candidate.skills),
                ]
            ).lower()
            matches = sum(1 for t in tokens if t in haystack)
            if matches:
                scored.append((candidate, matches / max(len(tokens), 1)))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        rows = [_candidate_row(c, s) for c, s in scored[:top_k]]
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={"query": query, "count": len(rows), "results": rows},
            summary=f"Matched {len(rows)} candidate(s) by keyword.",
            evidence_sources=["Candidate keyword search"],
            confidence=100.0 if rows else 0.0,
        )


class SkillGapTool(BaseTool):
    """JD skill-gap analysis for a candidate (wraps the skill-gap engine)."""

    metadata = ToolMetadata(
        name="skill_gap",
        description="Compute matched/missing JD skills for a candidate.",
        input_fields=["candidate_id", "jd"],
        engine="Skill Gap Analyzer",
    )

    def validate(self, tool_input: dict[str, Any]) -> None:
        if not tool_input.get("candidate_id"):
            raise ToolValidationError("skill_gap requires 'candidate_id'.")

    def execute(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        candidate = context.repository.get(str(tool_input["candidate_id"]))
        if candidate is None:
            raise ToolValidationError(f"Unknown candidate {tool_input['candidate_id']!r}.")
        jd = str(tool_input.get("jd") or context.jd or "")
        gap = get_skill_gap(candidate, jd)
        return ToolResult(
            name=self.metadata.name,
            ok=True,
            output={"candidate_id": candidate.candidate_id, **gap},
            summary=(
                f"{gap['match_percent']}% JD skill match "
                f"({len(gap['matched'])} matched, {len(gap['missing'])} missing)."
            ),
            evidence_sources=["Skill-gap analyzer"],
        )
