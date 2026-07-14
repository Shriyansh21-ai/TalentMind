"""Intent classification + tool planning.

`IntentClassifier` maps a recruiter message to a structured :class:`IntentResult`
using a **data-driven keyword-pattern registry** (Module 3 — no giant if-else
chains). `CopilotPlanner` turns that intent + conversation state into a concrete
:class:`CopilotPlan` of tool calls (Module 5 — minimal tool selection with
contextual reference resolution).
"""

from __future__ import annotations

import re
from typing import Dict, List

from src.ai.copilot.models import CopilotPlan, Entities, Intent, IntentResult
from src.ai.copilot.state import ConversationState
from src.ai.copilot.tool_selector import select_tools

# Data-driven intent patterns. Each intent has weighted keyword phrases; the
# classifier scores intents by summed weights of matched phrases.
_INTENT_PATTERNS: Dict[Intent, List[tuple]] = {
    Intent.COMPARE_CANDIDATES: [("compare", 3), ("versus", 3), (" vs ", 3), ("better than", 3), ("difference between", 2)],
    Intent.EXPLAIN_RANKING: [("why", 2), ("explain", 3), ("ranked", 3), ("ranking", 3), ("top of the list", 2)],
    Intent.GENERATE_HIRING_SUMMARY: [("hiring summary", 4), ("summary", 2), ("summarize", 3), ("brief me", 2)],
    Intent.GENERATE_INTERVIEW_PLAN: [("interview", 3), ("interview plan", 4), ("questions to ask", 3), ("interview questions", 4)],
    Intent.ANALYZE_CANDIDATE: [("analyze", 3), ("analysis", 3), ("assess", 3), ("evaluate", 3), ("tell me about", 2), ("deep dive", 2)],
    Intent.PIPELINE_QUESTION: [("pipeline", 3), ("stage", 2), ("shortlist", 2), ("shortlisted", 2), ("offer stage", 2), ("funnel", 2)],
    Intent.DASHBOARD_QUESTION: [("dashboard", 3), ("distribution", 2), ("how many", 2), ("overall stats", 2), ("across candidates", 2), ("average experience", 2)],
    Intent.SKILL_SEARCH: [("skill", 2), ("skills", 2), ("who knows", 3), ("experience with", 2), ("proficient in", 3)],
    Intent.RECOMMENDATION_QUESTION: [("should we hire", 4), ("recommend", 3), ("recommendation", 3), ("hire or not", 3), ("is a good fit", 2)],
    Intent.SEARCH_CANDIDATE: [("find", 3), ("search", 3), ("look for", 3), ("show me", 2), ("candidates who", 2), ("engineers", 1)],
}

# Small skill vocabulary for entity extraction (classifier-local; does not modify
# the deterministic skill engines).
_SKILL_VOCAB = [
    "python", "java", "golang", "rust", "c++", "javascript", "typescript",
    "react", "angular", "vue", "node", "django", "spring",
    "machine learning", "deep learning", "nlp", "llm", "rag", "langchain",
    "transformers", "pytorch", "tensorflow", "computer vision",
    "aws", "azure", "gcp", "kubernetes", "docker", "terraform",
    "spark", "airflow", "kafka", "sql", "snowflake", "faiss",
]

_CANDIDATE_ID_RE = re.compile(r"CAND[_-]?\d+", re.IGNORECASE)
_TOP_K_RE = re.compile(r"top\s+(\d+)")

# Words implying a reference to the in-focus candidate / comparison set.
_SINGULAR_REFS = ("this candidate", "that candidate", "him", "her", "them", "this person")
_PLURAL_REFS = ("these", "those", "them", "both", "the two", "the candidates")


class IntentClassifier:
    """Deterministic keyword-pattern intent classifier."""

    def classify(self, message: str, state: ConversationState) -> IntentResult:
        """Classify ``message`` into a structured :class:`IntentResult`."""
        text = f" {message.lower().strip()} "

        scores: Dict[str, float] = {}
        for intent, patterns in _INTENT_PATTERNS.items():
            score = sum(weight for phrase, weight in patterns if phrase in text)
            if score:
                scores[intent.value] = float(score)

        if scores:
            best_value = max(scores, key=scores.get)  # type: ignore[arg-type]
            intent = Intent(best_value)
            top = scores[best_value]
            confidence = min(100.0, 50.0 + top * 12.5)
        else:
            intent = Intent.GENERAL_HIRING_QUESTION
            confidence = 40.0

        entities = self._extract_entities(message, text)
        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            scores=scores,
        )

    def _extract_entities(self, raw_message: str, lowered: str) -> Entities:
        """Extract candidate ids, skills, top_k and the search query."""
        candidate_ids = [m.upper().replace("-", "_") for m in _CANDIDATE_ID_RE.findall(raw_message)]
        skills = [s for s in _SKILL_VOCAB if s in lowered]
        top_k = 5
        match = _TOP_K_RE.search(lowered)
        if match:
            top_k = max(1, min(20, int(match.group(1))))
        return Entities(
            candidate_ids=candidate_ids,
            skills=skills,
            query=raw_message.strip(),
            top_k=top_k,
        )


class CopilotPlanner:
    """Builds a :class:`CopilotPlan` from an intent + conversation state."""

    def __init__(self, classifier: IntentClassifier | None = None) -> None:
        self.classifier = classifier or IntentClassifier()

    def classify(self, message: str, state: ConversationState) -> IntentResult:
        """Classify a message (delegates to the classifier)."""
        return self.classifier.classify(message, state)

    def plan(self, intent_result: IntentResult, state: ConversationState) -> CopilotPlan:
        """Select the minimal tools and build their inputs for this request."""
        intent = intent_result.intent
        entities = intent_result.entities
        tool_names = select_tools(intent)

        candidate_id = self._resolve_candidate(entities, state)
        comparison_ids = self._resolve_comparison(entities, state)

        steps: List[tuple] = []
        for name in tool_names:
            tool_input = self._input_for(
                name, entities, candidate_id, comparison_ids
            )
            # Skip candidate-scoped tools we cannot satisfy (keeps plans minimal).
            if tool_input is None:
                continue
            steps.append((name, tool_input))

        rationale = (
            f"Intent '{intent.value}' → tools {[n for n, _ in steps] or 'none'} "
            "(minimal set required to answer)."
        )
        return CopilotPlan(
            intent=intent,
            steps=steps,
            rationale=rationale,
            focus_candidate=candidate_id,
            comparison_ids=comparison_ids,
        )

    # -- resolution helpers -------------------------------------------------

    def _resolve_candidate(self, entities: Entities, state: ConversationState) -> str | None:
        """Resolve the single candidate in focus from entities or state."""
        if entities.candidate_ids:
            return entities.candidate_ids[0]
        if state.current_candidate:
            return state.current_candidate
        if state.last_search_results:
            return state.last_search_results[0]
        return None

    def _resolve_comparison(self, entities: Entities, state: ConversationState) -> List[str]:
        """Resolve a comparison set from entities or state."""
        if len(entities.candidate_ids) >= 2:
            return entities.candidate_ids[:5]
        if len(state.current_comparison) >= 2:
            return state.current_comparison[:5]
        if len(state.last_search_results) >= 2:
            return state.last_search_results[:2]
        return list(entities.candidate_ids)

    def _input_for(
        self,
        name: str,
        entities: Entities,
        candidate_id: str | None,
        comparison_ids: List[str],
    ):
        """Build the input dict for tool ``name`` (or ``None`` to skip it)."""
        if name in ("faiss_search", "candidate_search"):
            return {"query": entities.query, "top_k": entities.top_k}
        if name == "comparison":
            if len(comparison_ids) < 2:
                return None
            return {"candidate_ids": comparison_ids}
        if name == "dashboard":
            return {}
        if name == "pipeline":
            return {"candidate_id": candidate_id} if candidate_id else {}
        # Remaining tools are single-candidate scoped.
        if candidate_id is None:
            return None
        return {"candidate_id": candidate_id}
