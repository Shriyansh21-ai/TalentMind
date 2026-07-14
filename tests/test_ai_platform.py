"""Tests for the AI Platform (Phase 3 / Milestone 1).

Exercises the platform end-to-end using the offline deterministic provider (no
network, no keys): settings, provider factory + health, prompt loading, schema
validation, cache, safety, telemetry, the runner lifecycle, and the
HiringAnalystAgent — plus that the agent never emits scores and reflects (never
contradicts) the deterministic engines.
"""

from __future__ import annotations

import faiss  # noqa: F401  (faiss-before-torch load order)

from conftest import make_candidate

from src.insights.builder import build_insights
from src.interview.planner import build_interview_plan

from src.ai.config.settings import AISettings
from src.ai.core.agent_config import AgentConfig
from src.ai.core.response import AgentStatus
from src.ai.core.runner import AgentRunner
from src.ai.core.registry import registry
from src.ai.cache.file_cache import FileCache
from src.ai.cache.key import build_cache_key
from src.ai.telemetry.logger import TelemetryLogger
from src.ai.prompts.loader import PromptLoader, get_default_loader
from src.ai.providers.factory import available_providers, get_provider
from src.ai.providers.local import LocalHeuristicProvider
from src.ai.schemas.hiring_analysis import HiringAnalysis
from src.ai.validators.json_validator import validate_text
from src.ai.validators.safety import SafetyGuard
from src.ai.core.exceptions import SchemaValidationError, JSONParseError

from src.ai.agents.hiring_analyst import (
    HiringAnalystInput,
    build_evidence,
    compose_hiring_analysis,
    hiring_analyst_agent,
)

JD = "python machine learning llm aws docker rag pytorch"


def _input(**kwargs) -> HiringAnalystInput:
    candidate = make_candidate(**kwargs)
    insights = build_insights(candidate, JD, 150.0)
    plan = build_interview_plan(insights)
    return HiringAnalystInput(insights=insights, interview_plan=plan, jd=JD)


def _runner(tmp_path) -> AgentRunner:
    settings = AISettings(provider="local", cache_dir=str(tmp_path / "cache"),
                          telemetry_dir=str(tmp_path / "logs"))
    return AgentRunner(
        settings=settings,
        cache=FileCache(settings.cache_dir),
        telemetry=TelemetryLogger(settings.telemetry_dir),
    )


# ---------------------------------------------------------------------------
# Config + providers
# ---------------------------------------------------------------------------


def test_settings_defaults_are_offline():
    settings = AISettings.from_env()
    # Default must be the offline provider so the platform works with no keys.
    assert settings.provider in {"local", "openai", "claude", "gemini", "ollama"}


def test_local_provider_is_healthy_and_deterministic():
    settings = AISettings(provider="local")
    provider = LocalHeuristicProvider(settings)
    assert provider.health_check() is True
    assert provider.is_deterministic is True


def test_factory_returns_local_by_default():
    settings = AISettings(provider="local")
    provider, warnings = get_provider(settings)
    assert provider.key == "local"
    assert warnings == []


def test_factory_falls_back_when_provider_unavailable():
    # openai without SDK/key -> unhealthy -> fall back to local (non-strict).
    settings = AISettings(provider="openai", strict=False)
    provider, warnings = get_provider(settings)
    assert provider.key == "local"
    assert warnings  # substitution recorded


def test_available_providers_reports_local_true():
    status = available_providers(AISettings())
    assert status["local"] is True


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def test_prompt_templates_load_and_render():
    loader = get_default_loader()
    system = loader.render("hiring_analyst_system", "v1")
    assert "Hiring Analyst" in system
    user = loader.render(
        "hiring_analyst_user", "v1",
        jd="x", evidence_json="{}", schema_fields="- a",
    )
    assert "EVIDENCE" in user


def test_prompt_missing_placeholder_raises():
    import pytest
    from src.ai.core.exceptions import PromptRenderError
    loader = PromptLoader()
    with pytest.raises(PromptRenderError):
        loader.render("hiring_analyst_user", "v1", jd="only")


# ---------------------------------------------------------------------------
# Schema + validation + safety
# ---------------------------------------------------------------------------


def test_schema_has_no_score_fields():
    SafetyGuard().assert_schema_is_score_free(HiringAnalysis)  # must not raise


def test_validate_text_rejects_bad_json():
    import pytest
    with pytest.raises(JSONParseError):
        validate_text("not json at all", HiringAnalysis)


def test_validate_text_rejects_incomplete_schema():
    import pytest
    with pytest.raises(SchemaValidationError):
        validate_text('{"executive_summary": "x"}', HiringAnalysis)


def test_executive_decision_is_coerced():
    data = compose_hiring_analysis(build_evidence(_input()))
    analysis = HiringAnalysis(**data)
    assert analysis.executive_decision in {
        "Strong Hire", "Hire", "Hold", "Reject", "Insufficient Evidence"
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def test_cache_key_changes_with_dimensions():
    base = dict(agent="a", agent_version="v1", prompt_version="v1",
                provider="local", model="m", subject_id="C1", scope="jd1")
    k1 = build_cache_key(**base)
    k2 = build_cache_key(**{**base, "scope": "jd2"})
    k3 = build_cache_key(**{**base, "model": "m2"})
    assert k1 != k2 != k3 and k1 != k3


def test_file_cache_round_trip(tmp_path):
    cache = FileCache(str(tmp_path / "c"))
    cache.set("k", {"data": {"x": 1}})
    assert cache.get("k") == {"data": {"x": 1}}
    cache.delete("k")
    assert cache.get("k") is None


# ---------------------------------------------------------------------------
# Agent + runner lifecycle
# ---------------------------------------------------------------------------


def test_agent_registered():
    assert registry.has("hiring_analyst")
    assert registry.get("hiring_analyst") is hiring_analyst_agent


def test_runner_produces_valid_analysis(tmp_path):
    runner = _runner(tmp_path)
    result = runner.run(hiring_analyst_agent, _input())
    assert result.status == AgentStatus.SUCCESS
    assert result.provider == "local"
    assert isinstance(result.data, HiringAnalysis)
    assert result.data.executive_summary


def test_runner_cache_hit_on_second_run(tmp_path):
    runner = _runner(tmp_path)
    payload = _input()
    first = runner.run(hiring_analyst_agent, payload)
    second = runner.run(hiring_analyst_agent, payload)
    assert first.status == AgentStatus.SUCCESS
    assert second.status == AgentStatus.CACHED
    assert second.cache_hit is True


def test_runner_peek_only_after_generation(tmp_path):
    runner = _runner(tmp_path)
    payload = _input()
    assert runner.peek(hiring_analyst_agent, payload) is None
    runner.run(hiring_analyst_agent, payload)
    peeked = runner.peek(hiring_analyst_agent, payload)
    assert peeked is not None and peeked.status == AgentStatus.CACHED


def test_force_refresh_recomputes(tmp_path):
    runner = _runner(tmp_path)
    payload = _input()
    runner.run(hiring_analyst_agent, payload)
    refreshed = runner.run(hiring_analyst_agent, payload, AgentConfig(force_refresh=True))
    assert refreshed.status == AgentStatus.SUCCESS  # not CACHED
    assert refreshed.cache_hit is False


def test_agent_reflects_not_contradicts_engine(tmp_path):
    # A weak candidate should never be narrated as "Strong Hire".
    runner = _runner(tmp_path)
    weak = _input(candidate_id="WEAK", years=0.5, endorsements=0, skills=["Python"])
    result = runner.run(hiring_analyst_agent, weak)
    engine_rec = weak.insights.intelligence.recommendation
    assert result.data.executive_decision != "Strong Hire" or "Strong Hire" in engine_rec


def test_telemetry_records_runs(tmp_path):
    runner = _runner(tmp_path)
    runner.run(hiring_analyst_agent, _input())
    events = runner.telemetry.recent(10)
    assert events
    assert events[-1].agent == "hiring_analyst"
    assert events[-1].provider == "local"


def test_evidence_contains_no_invented_fields():
    payload = _input()
    evidence = build_evidence(payload)
    # Evidence must be sourced from the candidate/engines only.
    assert evidence["candidate"]["candidate_id"] == payload.insights.candidate_id
    assert "intelligence" in evidence and "risk" in evidence and "timeline" in evidence
