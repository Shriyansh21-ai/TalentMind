# app.py
"""TalentMind — Enterprise Candidate Intelligence Platform.

Thin Streamlit orchestrator. It wires the (unchanged) scoring, semantic and
intelligence engines in ``src/`` to the presentation modules in ``src/ui/``:

    Load Data -> Rule Rank -> Semantic Rank -> Dashboard -> Search
             -> Candidate Cards -> Export

All ranking formulas, scoring, embeddings and recommendation logic live in
``src/`` and are invoked here without modification.
"""

import os

# NOTE: faiss must be imported before torch / sentence-transformers. On Windows
# the reverse OpenMP load order segfaults the process at import time. Importing
# faiss first here (the single entry point) guarantees a safe load order.
import faiss  # noqa: F401  (imported for load-order side effect only)

import streamlit as st

from src.ingestion.candidate_loader import load_candidates
from src.scoring.final_score import calculate_final_score
from src.scoring.hybrid_score import hybrid_score
from src.semantic.recruiter_search import build_search_index
from src.intelligence.jd_parser import parse_jd
from src.intelligence.jd_analyzer import analyze
from src.intelligence.dashboard import show_job_dashboard
from src.recruiter.pipeline import load_actions

from src.ui.sidebar import render_sidebar
from src.ui.dashboard import render_dashboard
from src.ui.workspace import render_enterprise_workspace
from src.ui.recruiter_search import render_recruiter_search
from src.ui.candidate_card import render_candidate_card
from src.ui.export import render_export

# --------------------------------------------------
# ENV
# --------------------------------------------------

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

CANDIDATES_PATH = "data/raw/candidates.jsonl"
SEMANTIC_POOL_SIZE = 1000
TOP_CANDIDATES = 20

# --------------------------------------------------
# PAGE
# --------------------------------------------------

st.set_page_config(
    page_title="TalentMind",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 TalentMind")

st.markdown(
    """
### Enterprise Candidate Intelligence Platform

AI-powered candidate discovery, semantic ranking,
skill gap analysis and recruiter workflow automation.
"""
)


# --------------------------------------------------
# CACHE
# --------------------------------------------------


@st.cache_data
def get_candidates():
    """Load and cache the candidate database (parsed once per session)."""
    return load_candidates(CANDIDATES_PATH)


@st.cache_resource
def initialize_faiss(candidates):
    """Build the FAISS search index once and cache it for the session."""
    build_search_index(candidates)
    return True


# --------------------------------------------------
# ORCHESTRATION
# --------------------------------------------------


def _render_copilot_workspace() -> None:
    """Render the AI Recruiter Copilot workspace (Phase 3 / Milestone 2).

    Kept as a small, self-contained branch so ``app.py`` stays a thin orchestrator.
    The candidate repository is built lazily (inside the copilot page) from the
    same cached loaders + FAISS index the console uses, so nothing heavy runs
    until the recruiter actually sends a message.
    """
    from src.ui.copilot_page import render_copilot
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_copilot(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_orchestration_workspace() -> None:
    """Render the Multi-Agent Orchestration console (Phase 3 / Milestone 3).

    Self-contained and fully offline: it drives the orchestration framework with
    generic demo agents, so it renders instantly and never loads the dataset or
    a provider. All logic lives in ``src/ai/orchestration``.
    """
    from src.ui.orchestration_page import render_orchestration

    render_orchestration()


def _render_resume_workspace() -> None:
    """Render the Resume Intelligence workspace (Phase 4 / Milestone 1).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console) and delegates to the ResumeAnalystAgent for recruiter-grade
    resume analysis. Resume quality only — never hiring ranking.
    """
    from src.ui.resume_intelligence_tab import render_resume_workspace
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_resume_workspace(_build_repository)


def _render_jd_workspace() -> None:
    """Render the JD Intelligence workspace (Phase 4 / Milestone 2).

    Fully self-contained and offline: the recruiter pastes a JD and the
    JDAnalystAgent produces enterprise JD intelligence. JD quality only — never
    candidate ranking. All logic lives in ``src/ai/agents/jd``.
    """
    from src.ui.jd_intelligence_tab import render_jd_workspace

    render_jd_workspace()


def _render_committee_workspace() -> None:
    """Render the AI Hiring Committee workspace (Phase 4 / Milestone 3).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console) and convenes the multi-agent committee, which only consumes
    cached structured outputs. All logic lives in ``src/ai/committee``.
    """
    from src.ui.committee_tab import render_committee_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_committee_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_executive_report_workspace() -> None:
    """Render the Executive Hiring Report workspace (Phase 4 / Milestone 4).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console) and synthesizes every existing intelligence output into a
    boardroom-grade executive report with PDF/DOCX/HTML/PPTX export. It consumes
    existing outputs only. All logic lives in ``src/ai/agents/executive_report``.
    """
    from src.ui.executive_report_tab import render_executive_report_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_executive_report_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_interview_studio_workspace() -> None:
    """Render the Enterprise AI Interview Studio workspace (Phase 4 / Milestone 5).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console) and synthesizes every existing intelligence output into a
    complete, personalized interview plan — strategy, adaptive question flow,
    rubrics, decision matrix, feedback templates and interviewer guides. It
    consumes existing outputs only. All logic lives in
    ``src/ai/agents/interview_studio``.
    """
    from src.ui.interview_studio_tab import render_interview_studio_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_interview_studio_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_compensation_workspace() -> None:
    """Render the Enterprise Compensation Governance workspace (Phase 5 / Milestone 1).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console) and synthesizes every existing intelligence output into a
    transparent, defensible compensation governance report — a defensible range,
    offer justification, governance checks, negotiation strategy and a flagship
    transparency audit trail. It consumes existing outputs only and fabricates no
    salary/market data. All logic lives in ``src/ai/agents/compensation``.
    """
    from src.ui.compensation_tab import render_compensation_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_compensation_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_pay_equity_workspace() -> None:
    """Render the Enterprise Pay Equity Guardian workspace (Phase 5 / Milestone 2).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console), reuses the Compensation Governance offer and evaluates internal
    fairness — compression, inversion, promotion equity, policy alignment and the
    executive-review chain. It fabricates no payroll and concludes no legal
    violation. All logic lives in ``src/ai/agents/pay_equity``.
    """
    from src.ui.pay_equity_tab import render_pay_equity_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_pay_equity_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_compliance_workspace() -> None:
    """Render the Enterprise Hiring Compliance workspace (Phase 5 / Milestone 3).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console), reuses the whole hiring-intelligence chain and evaluates whether
    the workflow follows company governance — required steps, approvals, policy,
    documentation, audit readiness and governance risk. It gives no legal advice
    and fabricates no compliance conclusion. All logic lives in
    ``src/ai/agents/compliance``.
    """
    from src.ui.compliance_tab import render_compliance_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_compliance_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_audit_workspace() -> None:
    """Render the Enterprise Hiring Audit & Explainability workspace (Phase 5 / M4).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console), reuses the whole hiring-intelligence chain (via the compliance
    engine) and reconstructs the complete decision journey — decision trace,
    evidence provenance, timeline, human-vs-AI responsibility and audit readiness.
    It never fabricates evidence/approvals/history. All logic lives in
    ``src/ai/agents/audit``.
    """
    from src.ui.audit_tab import render_audit_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_audit_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_hiring_intelligence_workspace() -> None:
    """Render the Enterprise Hiring Intelligence & Workforce Analytics workspace (Phase 5 / M5).

    Builds the candidate repository lazily (same cached loaders + FAISS index as
    the console) and aggregates the platform's existing per-candidate intelligence
    into organizational analytics — hiring health, KPIs, bottlenecks, team
    analytics, forecasts and optimization opportunities. It provides organizational
    intelligence only (never candidate ranking) and marks unavailable metrics
    honestly. All logic lives in ``src/ai/agents/hiring_intelligence``.
    """
    from src.ui.hiring_intelligence_tab import render_hiring_intelligence_workspace
    from src.ui.helpers import get_insights
    from src.ai.tools.provider import InMemoryCandidateRepository

    def _build_repository():
        candidates = get_candidates()
        initialize_faiss(candidates)
        from src.semantic.recruiter_search import recruiter_search

        return InMemoryCandidateRepository(
            candidates,
            search_fn=lambda query, k: recruiter_search(query, top_k=k),
        )

    render_hiring_intelligence_workspace(
        _build_repository,
        insights_fn=lambda candidate, jd: get_insights(candidate, jd),
    )


def _render_platform_admin_workspace() -> None:
    """Render the Platform Administration workspace (Phase 6 / Milestone 1).

    Fully self-contained and offline: an enterprise operations console over the
    additive ``src/platform`` foundation (organizations, tenants, identity,
    RBAC, subscriptions, configuration, audit and system health). It never loads
    the dataset or a provider, and touches no Phase 1-5 business logic.
    """
    from src.ui.platform_admin import render_platform_admin

    render_platform_admin()


def _render_integration_marketplace_workspace() -> None:
    """Render the Integration Marketplace workspace (Phase 6 / Milestone 2).

    Fully self-contained and offline: an enterprise integration console over the
    additive ``src/platform/integrations`` foundation (provider marketplace,
    installed integrations, health, webhooks, synchronization, event bus and
    developer SDKs). It never loads the dataset or a provider, makes no network
    call, and touches no Phase 1-5 business logic.
    """
    from src.ui.integration_marketplace import render_integration_marketplace

    render_integration_marketplace()


def _render_runtime_operations_workspace() -> None:
    """Render the Runtime Operations workspace (Phase 6 / Milestone 3).

    Fully self-contained and offline: an enterprise runtime console over the
    additive ``src/platform/runtime`` infrastructure (background jobs, workers,
    queues, cache, health, resilience, load management and resource
    utilization). It never loads the dataset or a provider, makes no network
    call, and touches no Phase 1-5 business logic.
    """
    from src.ui.runtime_operations import render_runtime_operations

    render_runtime_operations()


def _render_security_operations_workspace() -> None:
    """Render the Security & Operations Center workspace (Phase 6 / Milestone 4).

    Fully self-contained and offline: an enterprise security & operations console
    over the additive ``src/platform/security`` foundation (identity, audit,
    secrets, monitoring, governance, compliance, threat detection, configuration
    governance and incidents). It never loads the dataset or a provider, makes no
    network call, and touches no Phase 1-5 business logic.
    """
    from src.ui.security_operations import render_security_operations

    render_security_operations()


def main() -> None:
    """Drive the end-to-end recruiter pipeline for a single run."""
    workspace = st.sidebar.radio(
        "Workspace",
        [
            "Recruiter Console",
            "AI Recruiter Copilot",
            "Multi-Agent Orchestration",
            "Resume Intelligence",
            "JD Intelligence",
            "AI Hiring Committee",
            "Executive Hiring Report",
            "Interview Studio",
            "Compensation Governance",
            "Pay Equity Guardian",
            "Hiring Compliance",
            "Hiring Audit",
            "Hiring Intelligence",
            "Platform Administration",
            "Integration Marketplace",
            "Runtime Operations",
            "Security & Operations Center",
        ],
        key="workspace_nav",
    )
    if workspace == "Platform Administration":
        _render_platform_admin_workspace()
        return
    if workspace == "Integration Marketplace":
        _render_integration_marketplace_workspace()
        return
    if workspace == "Runtime Operations":
        _render_runtime_operations_workspace()
        return
    if workspace == "Security & Operations Center":
        _render_security_operations_workspace()
        return
    if workspace == "AI Recruiter Copilot":
        _render_copilot_workspace()
        return
    if workspace == "Multi-Agent Orchestration":
        _render_orchestration_workspace()
        return
    if workspace == "Resume Intelligence":
        _render_resume_workspace()
        return
    if workspace == "JD Intelligence":
        _render_jd_workspace()
        return
    if workspace == "AI Hiring Committee":
        _render_committee_workspace()
        return
    if workspace == "Executive Hiring Report":
        _render_executive_report_workspace()
        return
    if workspace == "Interview Studio":
        _render_interview_studio_workspace()
        return
    if workspace == "Compensation Governance":
        _render_compensation_workspace()
        return
    if workspace == "Pay Equity Guardian":
        _render_pay_equity_workspace()
        return
    if workspace == "Hiring Compliance":
        _render_compliance_workspace()
        return
    if workspace == "Hiring Audit":
        _render_audit_workspace()
        return
    if workspace == "Hiring Intelligence":
        _render_hiring_intelligence_workspace()
        return

    uploaded_jd, run_button = render_sidebar()

    if not run_button:
        return

    if uploaded_jd is None:
        st.error("Upload a Job Description first")
        st.stop()

    jd = uploaded_jd.read().decode("utf-8")

    if not jd.strip():
        st.error("The uploaded Job Description is empty")
        st.stop()

    # ---- Job Intelligence -------------------------------------------------
    job_profile = analyze(parse_jd(jd))
    show_job_dashboard(job_profile)

    # ---- Load candidates --------------------------------------------------
    with st.spinner("Loading candidate database..."):
        candidates = get_candidates()

    if not candidates:
        st.error("No candidates found in the database")
        st.stop()

    initialize_faiss(candidates)
    st.success(f"{len(candidates):,} Candidates Loaded")

    # ---- Rule-based ranking ----------------------------------------------
    with st.spinner("Running rule engine..."):
        ranked = sorted(candidates, key=calculate_final_score, reverse=True)

    # ---- Semantic (hybrid) ranking ---------------------------------------
    with st.spinner("Running semantic matching..."):
        results = [
            (candidate, round(hybrid_score(candidate, job_profile), 2))
            for candidate in ranked[:SEMANTIC_POOL_SIZE]
        ]
        results.sort(key=lambda x: x[1], reverse=True)

    st.success("Ranking Complete")

    if not results:
        st.warning("No candidates could be ranked for this job description.")
        return

    # ---- Render ----------------------------------------------------------
    actions = load_actions()
    render_dashboard(candidates, results, jd, actions)

    # ---- Enterprise Hiring Workspace (Phase 2 / Milestone 2) --------------
    # Analytics dashboard, talent-pool segmentation, smart filtering and the
    # candidate comparison workspace. Rendered from a single thin call so the
    # orchestrator stays small; all logic lives in ``src/ui/workspace.py``.
    render_enterprise_workspace(candidates, results, jd)

    render_recruiter_search()

    st.header("🏆 Top Ranked Candidates")
    for rank, (candidate, score) in enumerate(results[:TOP_CANDIDATES], start=1):
        render_candidate_card(rank, candidate, score, jd)

    render_export(results)


if __name__ == "__main__":
    main()

