"""Concrete :class:`CandidateRepository` implementations.

The in-memory repository is the default DI wiring: the UI builds it from the
loaded candidate pool (with FAISS semantic search injected), and tests build it
from a handful of synthetic candidates (with a keyword fallback). Tools never
know which is which.
"""

from __future__ import annotations

from collections.abc import Callable

from src.ai.tools.base import CandidateRepository
from src.models.candidates import Candidate


class InMemoryCandidateRepository(CandidateRepository):
    """Repository over an in-memory candidate list.

    Args:
        candidates: The candidate pool.
        search_fn: Optional semantic search function
            ``(query, top_k) -> [(candidate, score)]`` (e.g. FAISS-backed). When
            omitted, a deterministic keyword search over the pool is used, so the
            repository is fully functional offline / in tests.
    """

    def __init__(
        self,
        candidates: list[Candidate],
        search_fn: Callable[[str, int], list[tuple]] | None = None,
    ) -> None:
        self._candidates = list(candidates)
        self._by_id: dict[str, Candidate] = {c.candidate_id: c for c in candidates}
        self._search_fn = search_fn

    def get(self, candidate_id: str) -> Candidate | None:
        """Return a candidate by id (or ``None``)."""
        return self._by_id.get(candidate_id)

    def search(self, query: str, top_k: int = 5) -> list[tuple]:
        """Semantic search when available, else deterministic keyword search."""
        if self._search_fn is not None:
            return self._search_fn(query, top_k)
        return self._keyword_search(query, top_k)

    def sample(self, limit: int = 200) -> list[Candidate]:
        """Return up to ``limit`` candidates from the pool."""
        return self._candidates[:limit]

    def _keyword_search(self, query: str, top_k: int) -> list[tuple]:
        """Fallback keyword search (no embeddings)."""
        tokens = [t for t in query.lower().replace(",", " ").split() if t]
        scored: list[tuple] = []
        for candidate in self._candidates:
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
        return scored[:top_k]
