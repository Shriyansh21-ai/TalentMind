"""RecruiterCopilot controller — the copilot lifecycle orchestrator (Module 1).

Ties together conversation management, intent classification + planning, tool
execution, the AI Platform (narration), and response building. It never bypasses
a deterministic engine: every fact in a reply originates from a tool that wrapped
an existing engine.

All collaborators are injected (SOLID / DI), so the controller is fully testable
with a synthetic repository and no network.
"""

from __future__ import annotations

import time
from typing import Callable, List, Optional

from src.models.candidates import Candidate
from src.insights.models import CandidateInsights

from src.ai.core.runner import AgentRunner
from src.ai.tools.base import CandidateRepository, ToolContext, ToolResult
from src.ai.tools.registry import ToolRegistry, ToolRunner, registry as default_registry
import src.ai.tools.builtin  # noqa: F401  (registers built-in tools on import)

from src.ai.agents.recruiter_copilot import (
    RecruiterCopilotInput,
    recruiter_copilot_agent,
)
from src.ai.copilot.conversation import ConversationManager
from src.ai.copilot.models import CopilotPlan, CopilotTurn
from src.ai.copilot.planner import CopilotPlanner
from src.ai.copilot.response_builder import build_turn
from src.ai.copilot.session import CopilotSession
from src.ai.copilot.state import ConversationState

InsightsFn = Callable[[Candidate, str], CandidateInsights]


class RecruiterCopilot:
    """Enterprise Recruiter Copilot controller."""

    def __init__(
        self,
        repository: CandidateRepository,
        *,
        tool_registry: Optional[ToolRegistry] = None,
        ai_runner: Optional[AgentRunner] = None,
        planner: Optional[CopilotPlanner] = None,
        conversation: Optional[ConversationManager] = None,
        insights_fn: Optional[InsightsFn] = None,
    ) -> None:
        """Wire the copilot's collaborators (DI; sensible defaults used)."""
        self.repository = repository
        self.tool_registry = tool_registry or default_registry
        self.tool_runner = ToolRunner(self.tool_registry)
        self.ai_runner = ai_runner or AgentRunner()
        self.planner = planner or CopilotPlanner()
        self.conversation = conversation or ConversationManager()
        self.insights_fn = insights_fn

    def ask(self, session_id: str, message: str, jd: str = "") -> CopilotTurn:
        """Handle one recruiter message and return a full :class:`CopilotTurn`.

        Lifecycle: classify → plan → run tools → narrate (AI Platform) → build
        turn → record conversation.
        """
        start = time.perf_counter()

        session = self.conversation.get_or_create(session_id)
        state = session.state
        if jd:
            state.current_jd = jd

        # 1) Understand + plan (minimal tools).
        intent_result = self.planner.classify(message, state)
        plan = self.planner.plan(intent_result, state)

        # 2) Execute selected tools against the deterministic engines.
        context = ToolContext(
            repository=self.repository,
            jd=state.current_jd,
            insights_fn=self.insights_fn,
        )
        tool_results = self.tool_runner.run_many(plan.steps, context)

        # 3) Update conversation working state, then backfill the plan's resolved
        #    references from post-execution state (e.g. the top search hit) so the
        #    suggested actions reflect what we just discovered.
        self._update_state(state, plan, tool_results)
        if not plan.focus_candidate and state.current_candidate:
            plan.focus_candidate = state.current_candidate
        if len(plan.comparison_ids) < 2 and len(state.last_search_results) >= 2:
            plan.comparison_ids = state.last_search_results[:2]

        # 4) Narrate via the AI Platform (structured tool outputs only).
        tool_outputs = {r.name: r.output for r in tool_results if r.ok}
        ai_input = RecruiterCopilotInput(
            intent=plan.intent.value,
            message=message,
            tool_outputs=tool_outputs,
        )
        ai_result = self.ai_runner.run(recruiter_copilot_agent, ai_input)

        # 5) Assemble + record.
        latency_ms = (time.perf_counter() - start) * 1000.0
        turn = build_turn(message, intent_result, plan, tool_results, ai_result, latency_ms)
        self.conversation.record(session, message, turn)
        return turn

    def session(self, session_id: str) -> CopilotSession:
        """Return (creating if needed) the session for ``session_id``."""
        return self.conversation.get_or_create(session_id)

    def reset(self, session_id: str) -> None:
        """Reset a conversation."""
        self.conversation.reset(session_id)

    # -- internals ----------------------------------------------------------

    def _update_state(
        self,
        state: ConversationState,
        plan: CopilotPlan,
        tool_results: List[ToolResult],
    ) -> None:
        """Update the working state from the plan + tool results."""
        if plan.focus_candidate:
            state.focus_candidate(plan.focus_candidate)
        if plan.comparison_ids:
            state.set_comparison(plan.comparison_ids)

        for result in tool_results:
            if result.ok and result.name in ("faiss_search", "candidate_search"):
                ids = [
                    row.get("candidate_id")
                    for row in result.output.get("results", [])
                    if row.get("candidate_id")
                ]
                if ids:
                    state.record_search(ids)
                    if not state.current_candidate:
                        state.focus_candidate(ids[0])


def build_recruiter_copilot(
    repository: CandidateRepository,
    *,
    insights_fn: Optional[InsightsFn] = None,
    ai_runner: Optional[AgentRunner] = None,
) -> RecruiterCopilot:
    """Factory building a :class:`RecruiterCopilot` with default collaborators."""
    return RecruiterCopilot(
        repository, insights_fn=insights_fn, ai_runner=ai_runner
    )
