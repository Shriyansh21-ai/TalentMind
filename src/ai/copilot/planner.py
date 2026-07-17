"""Intent classification + tool planning.

`IntentClassifier` maps a recruiter message to a structured :class:`IntentResult`
using a **data-driven keyword-pattern registry** (Module 3 — no giant if-else
chains). `CopilotPlanner` turns that intent + conversation state into a concrete
:class:`CopilotPlan` of tool calls (Module 5 — minimal tool selection with
contextual reference resolution).
"""

from __future__ import annotations

import re

from src.ai.copilot.models import CopilotPlan, Entities, Intent, IntentResult
from src.ai.copilot.state import ConversationState
from src.ai.copilot.tool_selector import select_tools

# Data-driven intent patterns. Each intent has weighted keyword phrases; the
# classifier scores intents by summed weights of matched phrases.
_INTENT_PATTERNS: dict[Intent, list[tuple]] = {
    Intent.COMPARE_CANDIDATES: [
        ("compare", 3),
        ("versus", 3),
        (" vs ", 3),
        ("better than", 3),
        ("difference between", 2),
    ],
    Intent.EXPLAIN_RANKING: [
        ("why", 2),
        ("explain", 3),
        ("ranked", 3),
        ("ranking", 3),
        ("top of the list", 2),
    ],
    Intent.GENERATE_HIRING_SUMMARY: [
        ("hiring summary", 4),
        ("summary", 2),
        ("summarize", 3),
        ("brief me", 2),
    ],
    Intent.GENERATE_INTERVIEW_PLAN: [
        ("interview", 3),
        ("interview plan", 4),
        ("questions to ask", 3),
        ("interview questions", 4),
    ],
    Intent.ANALYZE_CANDIDATE: [
        ("analyze", 3),
        ("analysis", 3),
        ("assess", 3),
        ("evaluate", 3),
        ("tell me about", 2),
        ("deep dive", 2),
    ],
    Intent.PIPELINE_QUESTION: [
        ("pipeline", 3),
        ("stage", 2),
        ("shortlist", 2),
        ("shortlisted", 2),
        ("offer stage", 2),
        ("funnel", 2),
    ],
    Intent.DASHBOARD_QUESTION: [
        ("dashboard", 3),
        ("distribution", 2),
        ("how many", 2),
        ("overall stats", 2),
        ("across candidates", 2),
        ("average experience", 2),
    ],
    Intent.SKILL_SEARCH: [
        ("skill", 2),
        ("skills", 2),
        ("who knows", 3),
        ("experience with", 2),
        ("proficient in", 3),
    ],
    Intent.RECOMMENDATION_QUESTION: [
        ("should we hire", 4),
        ("recommend", 3),
        ("recommendation", 3),
        ("hire or not", 3),
        ("is a good fit", 2),
    ],
    Intent.RESUME_REVIEW: [
        ("resume", 3),
        ("cv", 3),
        ("ats", 4),
        ("resume quality", 4),
        ("review this resume", 5),
        ("review the resume", 5),
        ("what is weak", 3),
        ("weak", 2),
        ("how can", 2),
        ("improve", 2),
        ("ats friendly", 4),
        ("ats-friendly", 4),
    ],
    Intent.JD_ANALYSIS: [
        ("job description", 6),
        ("this jd", 5),
        ("the jd", 5),
        ("jd", 4),
        ("job posting", 5),
        ("job spec", 5),
        ("this role", 3),
        ("what level", 3),
        ("seniority", 2),
        ("well written", 3),
        ("hiring expectation", 3),
        ("expectation realistic", 3),
        ("realistic", 2),
        ("actually mandatory", 4),
        ("mandatory", 2),
        ("this job description", 6),
    ],
    Intent.HIRING_COMMITTEE: [
        ("hiring committee", 6),
        ("run committee", 5),
        ("run the committee", 6),
        ("committee", 4),
        ("convene", 4),
        ("panel", 3),
        ("disagree on", 4),
        ("disagree", 2),
        ("why was this candidate rejected", 5),
        ("why reject", 3),
        ("evidence supports hiring", 4),
        ("evidence support", 3),
        ("concerns remain", 4),
        ("committee decide", 4),
    ],
    Intent.INTERVIEW_STUDIO: [
        ("interview studio", 7),
        ("generate interview", 5),
        ("generate an interview", 5),
        ("generate a interview", 5),
        ("create interview", 5),
        ("build interview", 5),
        ("build an interview", 5),
        ("full interview", 5),
        ("complete interview", 5),
        ("interviewer packet", 7),
        ("interviewer guide", 6),
        ("interviewer kit", 6),
        ("interview kit", 6),
        ("backend interview", 5),
        ("frontend interview", 5),
        ("ml interview", 5),
        ("system design interview", 5),
        ("behavioral interview", 5),
        ("technical interview", 4),
        ("interview this", 5),
        ("interview a ", 4),
        ("questions validate", 6),
        ("validate the committee", 6),
        ("validate committee", 5),
        ("committee concerns", 5),
        ("evaluation rubric", 5),
        ("interview rubric", 5),
        ("decision matrix", 5),
        ("risk validation question", 5),
        ("interview strategy", 5),
        ("adaptive question", 5),
    ],
    Intent.EXECUTIVE_REPORT: [
        ("executive report", 6),
        ("executive hiring report", 7),
        ("executive summary", 5),
        ("generate report", 4),
        ("generate a report", 4),
        ("generate executive", 5),
        ("create report", 4),
        ("cto report", 6),
        ("ceo report", 6),
        ("hr report", 5),
        ("recruiter report", 5),
        ("hiring manager report", 6),
        ("committee report", 5),
        ("candidate report", 5),
        ("interview packet", 6),
        ("board report", 5),
        ("board briefing", 5),
        ("briefing", 3),
        ("export", 4),
        ("download", 3),
        ("as pdf", 4),
        ("as a pdf", 4),
        ("pptx", 4),
        ("powerpoint", 4),
        ("as docx", 3),
        ("as a word", 3),
        ("report for", 3),
        ("boardroom", 4),
    ],
    Intent.COMPENSATION_GOVERNANCE: [
        ("compensation governance", 7),
        ("compensation report", 6),
        ("compensation range", 6),
        ("compensation", 4),
        ("offer justification", 6),
        ("justify the offer", 5),
        ("justify this offer", 5),
        ("finance approval report", 7),
        ("finance approval", 6),
        ("finance sign", 5),
        ("negotiation strategy", 6),
        ("negotiation", 4),
        ("negotiate", 3),
        ("why are we offering", 6),
        ("offering this compensation", 6),
        ("why this compensation", 6),
        ("why this salary", 5),
        ("offering this salary", 5),
        ("salary range", 5),
        ("salary recommendation", 6),
        ("pay band", 5),
        ("pay range", 5),
        ("how much should we pay", 6),
        ("how much to pay", 6),
        ("what should we pay", 6),
        ("explain executive reasoning", 6),
        ("executive reasoning", 5),
        ("explain the reasoning", 4),
        ("audit trail", 5),
        ("offer strategy", 5),
        ("comp report", 5),
        ("defensible", 3),
    ],
    Intent.PAY_EQUITY: [
        ("pay equity report", 7),
        ("pay equity", 6),
        ("pay-equity", 6),
        ("internal equity", 6),
        ("internal fairness", 6),
        ("is this offer fair", 6),
        ("is this fair", 5),
        ("offer fair", 5),
        ("fair offer", 5),
        ("fairness", 4),
        ("compression risk", 6),
        ("salary compression", 6),
        ("compression", 5),
        ("pay inversion", 6),
        ("inversion", 5),
        ("who should approve", 6),
        ("who approves", 5),
        ("should approve this", 5),
        ("who needs to approve", 6),
        ("approval chain", 5),
        ("does this violate pay policy", 7),
        ("violate pay policy", 6),
        ("pay policy", 5),
        ("policy violation", 5),
        ("promotion equity", 6),
        ("promotion inequity", 6),
        ("equity risk", 5),
        ("equity check", 5),
        ("check equity", 5),
        ("equity", 3),
        ("fair to existing", 5),
    ],
    Intent.HIRING_COMPLIANCE: [
        ("hiring compliance", 7),
        ("compliance report", 7),
        ("is this hiring process compliant", 7),
        ("hiring process compliant", 6),
        ("process compliant", 5),
        ("is this compliant", 6),
        ("compliant", 4),
        ("compliance", 4),
        ("workflow compliance", 6),
        ("governance check", 5),
        ("policy compliance", 5),
        ("compliance policy", 5),
        ("what approvals are missing", 7),
        ("approvals are missing", 6),
        ("approvals missing", 6),
        ("missing approval", 5),
        ("what approvals", 5),
        ("executive approval required", 6),
        ("is executive approval", 6),
        ("executive approval", 5),
        ("approval required", 5),
        ("approval matrix", 5),
        ("required approvals", 4),
        ("show audit trail", 7),
        ("audit trail", 6),
        ("audit readiness", 5),
        ("what documentation is missing", 7),
        ("documentation is missing", 6),
        ("missing documentation", 6),
        ("documentation missing", 6),
        ("documentation", 4),
        ("governance", 3),
    ],
    Intent.HIRING_AUDIT: [
        ("why was this candidate hired", 7),
        ("why was this candidate", 5),
        ("why hired", 5),
        ("why was this hire", 5),
        ("explain this hiring decision", 7),
        ("explain the hiring decision", 7),
        ("explain this decision", 6),
        ("explain the decision", 5),
        ("hiring decision", 4),
        ("decision timeline", 6),
        ("hiring timeline", 6),
        ("show timeline", 5),
        ("show decision", 5),
        ("timeline", 3),
        ("show evidence", 6),
        ("show the evidence", 6),
        ("evidence graph", 6),
        ("evidence provenance", 6),
        ("provenance", 5),
        ("generate audit report", 7),
        ("audit report", 7),
        ("generate audit", 6),
        ("explainability", 6),
        ("reconstruct", 5),
        ("decision trace", 6),
        ("decision journey", 6),
        ("approval history", 6),
        ("who approved", 5),
        ("decision history", 5),
        ("audit", 4),
    ],
    Intent.HIRING_INTELLIGENCE: [
        ("hiring intelligence", 7),
        ("workforce analytics", 7),
        ("workforce report", 7),
        ("executive workforce", 7),
        ("hiring analytics", 7),
        ("workforce", 5),
        ("how healthy is our hiring", 7),
        ("healthy is our hiring", 6),
        ("hiring health", 6),
        ("how healthy", 4),
        ("hiring organization", 6),
        ("bottlenecks", 6),
        ("bottleneck", 6),
        ("hiring trends", 6),
        ("hiring volume", 5),
        ("which departments need improvement", 7),
        ("which departments", 6),
        ("departments need improvement", 6),
        ("department comparison", 5),
        ("hiring kpi", 6),
        ("hiring kpis", 6),
        ("workforce intelligence", 7),
        ("hiring dashboard", 5),
        ("analytics", 3),
        ("trends", 3),
    ],
    Intent.SEARCH_CANDIDATE: [
        ("find", 3),
        ("search", 3),
        ("look for", 3),
        ("show me", 2),
        ("candidates who", 2),
        ("engineers", 1),
    ],
}

# Small skill vocabulary for entity extraction (classifier-local; does not modify
# the deterministic skill engines).
_SKILL_VOCAB = [
    "python",
    "java",
    "golang",
    "rust",
    "c++",
    "javascript",
    "typescript",
    "react",
    "angular",
    "vue",
    "node",
    "django",
    "spring",
    "machine learning",
    "deep learning",
    "nlp",
    "llm",
    "rag",
    "langchain",
    "transformers",
    "pytorch",
    "tensorflow",
    "computer vision",
    "aws",
    "azure",
    "gcp",
    "kubernetes",
    "docker",
    "terraform",
    "spark",
    "airflow",
    "kafka",
    "sql",
    "snowflake",
    "faiss",
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

        scores: dict[str, float] = {}
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

        steps: list[tuple] = []
        for name in tool_names:
            tool_input = self._input_for(name, entities, candidate_id, comparison_ids)
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

    def _resolve_comparison(self, entities: Entities, state: ConversationState) -> list[str]:
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
        comparison_ids: list[str],
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
        if name == "jd_analysis":
            return {}  # JD analysis reads the conversation's current JD from context
        if name == "pipeline":
            return {"candidate_id": candidate_id} if candidate_id else {}
        if name == "executive_report":
            # Pass the raw message so the tool can route template/packet/format.
            if candidate_id is None:
                return None
            return {"candidate_id": candidate_id, "message": entities.query}
        if name == "interview_studio":
            # Pass the raw message so the tool can route the role path + depth.
            if candidate_id is None:
                return None
            return {"candidate_id": candidate_id, "message": entities.query}
        if name == "compensation_governance":
            if candidate_id is None:
                return None
            return {"candidate_id": candidate_id, "message": entities.query}
        if name == "pay_equity_guardian":
            if candidate_id is None:
                return None
            return {"candidate_id": candidate_id, "message": entities.query}
        if name == "hiring_compliance":
            if candidate_id is None:
                return None
            return {"candidate_id": candidate_id, "message": entities.query}
        if name == "hiring_audit":
            if candidate_id is None:
                return None
            return {"candidate_id": candidate_id, "message": entities.query}
        if name == "hiring_intelligence":
            return {}  # organization-level analytics; no candidate needed

        # Remaining tools are single-candidate scoped.
        if candidate_id is None:
            return None
        return {"candidate_id": candidate_id}
