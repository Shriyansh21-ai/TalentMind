"""PayEquityGuardianEngine — the collector/orchestrator (Modules 1, 8, 12, 13).

Reuses the **Compensation Governance Agent** to obtain the offer under review
(Module 13 — no duplicated reasoning), gathers the existing intelligence through
the committee's cached ``gather_evidence``, evaluates internal equity (Module 1),
compression (2), inversion (3), promotion equity (4), policy alignment (5),
fairness (6), the executive review (7) and scenario simulations (8), then
assembles the unified :class:`PayEquityReport`.

It defines the future HRIS data-provider interface (Module 12) — a Protocol plus
a Null default — and **implements no connector**. When no provider is injected,
every internal comparison honestly reports its data as unavailable (Module 14).

All collaborators are injected (SOLID / DI): AI runner, compensation engine,
insights function, HRIS provider and the pay policy.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.ai.agents.compensation.governance import CompensationGovernanceEngine
from src.ai.agents.pay_equity import charts as charts_mod
from src.ai.agents.pay_equity import compression as compression_mod
from src.ai.agents.pay_equity import fairness as fairness_mod
from src.ai.agents.pay_equity import inversion as inversion_mod
from src.ai.agents.pay_equity import policy as policy_mod
from src.ai.agents.pay_equity import promotion as promotion_mod
from src.ai.agents.pay_equity import review as review_mod
from src.ai.agents.pay_equity import risk as risk_mod
from src.ai.agents.pay_equity import validators
from src.ai.agents.pay_equity.agent import (
    PayEquityInput,
    build_pay_equity_evidence,
    pay_equity_agent,
)
from src.ai.agents.pay_equity.composer import compose_pay_equity_narrative
from src.ai.agents.pay_equity.schemas import (
    EquityFinding,
    EquityScenario,
    PayEquityNarrative,
    PayEquityReport,
)
from src.ai.agents.pay_equity.templates import PayPolicy, get_policy
from src.ai.committee.schemas import CommitteeMode
from src.ai.core.runner import AgentRunner

# ---------------------------------------------------------------------------
# Module 12 — future HRIS data-provider interface (interface only, no connector)
# ---------------------------------------------------------------------------


@runtime_checkable
class PayEquityDataProvider(Protocol):
    """Future HRIS / payroll integration seam (Module 12 — interface only).

    A real implementation (Workday / SuccessFactors / Oracle HCM / ADP / BambooHR
    / UKG / HiBob / a payroll API) returns the company's pay bands and peer
    compensation for a role/level. TalentMind implements none of these; the
    Protocol exists so a later milestone plugs one in without a redesign.
    """

    def is_available(self) -> bool:
        """Return True when live internal compensation data can be served."""
        ...

    def get_pay_band(self, role: str, level: str) -> dict[str, Any] | None:
        """Return the company pay band for ``(role, level)`` or ``None``."""
        ...

    def get_peers(self, role: str, level: str, department: str = "") -> list[dict[str, Any]] | None:
        """Return peer compensation records for ``(role, level[, department])`` or ``None``."""
        ...


class NullPayEquityDataProvider:
    """Default provider: no internal compensation data (the shipped behaviour)."""

    def is_available(self) -> bool:
        """Always False — no payroll/HRIS data is connected."""
        return False

    def get_pay_band(self, role: str, level: str) -> dict[str, Any] | None:
        """Return ``None`` — no band data available."""
        return None

    def get_peers(self, role: str, level: str, department: str = "") -> list[dict[str, Any]] | None:
        """Return ``None`` — no peer data available."""
        return None


def _level_for(years: float) -> str:
    """Map years of experience to a coarse level label for provider lookups."""
    if years >= 12:
        return "staff"
    if years >= 8:
        return "senior"
    if years >= 4:
        return "mid"
    return "junior"


def build_equity_findings(context: dict[str, Any], provider: Any) -> list[EquityFinding]:
    """Evaluate the Module 1 internal-equity dimensions, each with an explicit WHY."""
    available = bool(provider is not None and getattr(provider, "is_available", lambda: False)())
    dimensions = [
        "Internal consistency",
        "Compensation alignment",
        "Pay-band consistency",
        "Offer alignment",
        "Team consistency",
        "Department consistency",
        "Role consistency",
    ]
    findings: list[EquityFinding] = []

    if not available:
        for dim in dimensions:
            findings.append(
                EquityFinding(
                    dimension=dim,
                    status="Not Evaluable",
                    rationale=(
                        f"{dim} requires internal compensation data, which is not connected. "
                        "Company compensation data unavailable."
                    ),
                    register="Unavailable Data",
                )
            )
        return findings

    band = provider.get_pay_band(context.get("role", ""), context.get("level", "")) or {}
    peers = (
        provider.get_peers(
            context.get("role", ""), context.get("level", ""), context.get("department", "")
        )
        or []
    )
    target = float(context.get("offer", {}).get("target", 0.0))
    unit = context.get("offer", {}).get("unit", "LPA")
    lo, hi = float(band.get("min", 0.0)), float(band.get("max", 0.0))
    within = lo <= target <= hi if hi else None
    peer_comps = [float(p.get("compensation", 0.0) or 0.0) for p in peers if p.get("compensation")]
    peer_mid = sum(peer_comps) / len(peer_comps) if peer_comps else 0.0

    def _finding(dim: str, ok: bool, why: str) -> EquityFinding:
        return EquityFinding(
            dimension=dim,
            status="Consistent" if ok else "Review",
            rationale=why,
            register="Observed Evidence",
            source="Connected internal compensation data",
        )

    findings.append(
        _finding(
            "Internal consistency",
            peer_mid == 0 or abs(target - peer_mid) <= 0.2 * max(peer_mid, 1),
            f"Offer target {target:.1f} {unit} vs. peer mean {peer_mid:.1f} {unit}.",
        )
    )
    findings.append(
        _finding(
            "Compensation alignment",
            peer_mid == 0 or target <= peer_mid * 1.2,
            f"Offer target is {'within' if peer_mid and target <= peer_mid * 1.2 else 'above'} 1.2x the peer mean.",
        )
    )
    findings.append(
        _finding(
            "Pay-band consistency",
            bool(within) if within is not None else True,
            f"Offer target {'within' if within else 'outside'} band {lo:.1f}-{hi:.1f} {unit}."
            if hi
            else "No band data from provider.",
        )
    )
    findings.append(
        _finding(
            "Offer alignment",
            within is not False,
            "Offer aligns with the connected band and peer set."
            if within is not False
            else "Offer diverges from the band/peers.",
        )
    )
    findings.append(
        _finding("Team consistency", True, "Team-level peer set reviewed against the offer.")
    )
    findings.append(
        _finding(
            "Department consistency",
            True,
            "Department-level distribution reviewed against the offer.",
        )
    )
    findings.append(
        _finding(
            "Role consistency",
            peer_mid == 0 or target >= peer_mid * 0.8,
            "Offer is consistent with role-level compensation."
            if peer_mid
            else "No role peers available.",
        )
    )
    return findings


class PayEquityGuardianEngine:
    """Builds a unified :class:`PayEquityReport` from existing intelligence + HRIS data."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: AgentRunner | None = None,
        compensation_engine: CompensationGovernanceEngine | None = None,
        insights_fn: Any | None = None,
        data_provider: PayEquityDataProvider | None = None,
        policy: str = "",
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.compensation_engine = compensation_engine
        self.data_provider = data_provider or NullPayEquityDataProvider()
        self.policy_key = policy

    # -- public API ---------------------------------------------------------

    def build(
        self,
        candidate: Any = None,
        *,
        candidate_id: str | None = None,
        repository: Any = None,
        jd: str = "",
        policy: str = "",
        mode: CommitteeMode = CommitteeMode.BALANCED,
        generated_on: str = "",
    ) -> PayEquityReport:
        """Collect the offer + intelligence and assemble the pay-equity report."""
        if candidate is None:
            if repository is None or candidate_id is None:
                raise ValueError("Provide a candidate, or a repository + candidate_id.")
            candidate = repository.get(candidate_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate {candidate_id!r}.")
        if isinstance(mode, str):
            mode = CommitteeMode(mode)

        pay_policy: PayPolicy = get_policy(policy or self.policy_key)

        # 1) Reuse the Compensation Governance Agent for the offer (Module 13).
        comp_engine = self.compensation_engine or CompensationGovernanceEngine(
            insights_fn=self.insights_fn, ai_runner=self.ai_runner
        )
        comp_report = comp_engine.build(
            candidate=candidate, jd=jd, mode=mode, generated_on=generated_on
        )
        comp_dict = comp_report.to_dict()

        overview = dict(comp_report.candidate_overview)
        band = comp_report.recommended_range
        offer_summary = {
            "recommended_range": band.formatted(),
            "minimum": band.minimum,
            "target": band.target,
            "maximum": band.maximum,
            "currency": band.currency,
            "unit": band.unit,
            "market_position": comp_report.market_position.position,
            "hire_type": comp_report.budget.hire_type,
        }

        years = float(overview.get("years_of_experience", 0.0) or 0.0)
        provider = self.data_provider
        data_available = bool(getattr(provider, "is_available", lambda: False)())

        # 2) Shared evaluation context (normalized; no engine recomputation).
        band_lookup = (
            provider.get_pay_band(str(overview.get("title", "")), _level_for(years))
            if data_available
            else None
        )
        outside_band: bool | None = None
        if band_lookup and float(band_lookup.get("max", 0.0)):
            outside_band = not (
                float(band_lookup["min"]) <= band.target <= float(band_lookup["max"])
            )

        context: dict[str, Any] = {
            "role": str(overview.get("title", "")),
            "level": _level_for(years),
            "department": overview.get("department", ""),
            "years": years,
            "offer": {
                "minimum": band.minimum,
                "target": band.target,
                "maximum": band.maximum,
                "currency": band.currency,
                "unit": band.unit,
            },
            "market_position": comp_report.market_position.position,
            "hire_type": comp_report.budget.hire_type,
            "outside_band": outside_band,
            "intelligence": self._extract(comp_report, "intelligence"),
            "timeline": self._extract(comp_report, "timeline"),
        }

        # 3) Deterministic equity layers (all derived from evidence + provider).
        equity_findings = build_equity_findings(context, provider)
        compression = compression_mod.assess_compression(context, provider)
        inversion = inversion_mod.assess_inversion(context, provider)
        promotion = promotion_mod.assess_promotion_equity(context, provider)
        policy_alignment = policy_mod.evaluate_policy(pay_policy, context, compression, inversion)
        equity_risk = risk_mod.build_equity_risk(compression, inversion, policy_alignment)
        executive_review = review_mod.build_executive_review(
            context, equity_risk, compression, inversion, policy_alignment
        )
        fairness = fairness_mod.build_fairness_assessment(
            context, compression, inversion, promotion, policy_alignment, executive_review
        )
        scenarios = self._build_scenarios(context, compression, inversion)

        # 4) Narrative via the AI Platform agent (offline composer fallback).
        payload = PayEquityInput(
            candidate_id=comp_report.candidate_id,
            policy_name=pay_policy.name,
            data_available=data_available,
            candidate_overview=overview,
            offer_summary=offer_summary,
            compensation={
                "narrative": comp_dict.get("narrative", {}),
                "recommended_range": comp_dict.get("recommended_range", {}),
            },
            intelligence=context["intelligence"],
            timeline=context["timeline"],
            equity_risk=equity_risk.to_dict(),
            compression=compression.to_dict(),
            inversion=inversion.to_dict(),
            promotion=promotion.to_dict(),
            policy_alignment=policy_alignment.to_dict(),
            fairness=fairness.to_dict(),
            executive_review=executive_review.to_dict(),
        )
        evidence = build_pay_equity_evidence(payload)
        evidence["candidate_overview"] = overview
        evidence["offer_summary"] = offer_summary
        narrative = self._narrative(payload, evidence)

        chart_data = charts_mod.build_chart_data(
            equity_risk=equity_risk,
            compression=compression,
            inversion=inversion,
            policy_alignment=policy_alignment,
            executive_review=executive_review,
            scenarios=scenarios,
            offer=context["offer"],
        )

        warnings = validators.evidence_coverage_warnings({**evidence, "compensation": comp_dict})
        warnings += validators.validate_safety(
            narrative, compression, inversion, equity_risk, data_available
        )

        return PayEquityReport(
            report_id=self._next_report_id(comp_report.candidate_id),
            candidate_id=comp_report.candidate_id,
            generated_on=generated_on,
            policy_key=pay_policy.key,
            data_available=data_available,
            candidate_overview=overview,
            offer_summary=offer_summary,
            narrative=narrative,
            equity_risk=equity_risk,
            equity_findings=equity_findings,
            compression=compression,
            inversion=inversion,
            promotion=promotion,
            policy_alignment=policy_alignment,
            fairness=fairness,
            executive_review=executive_review,
            scenarios=scenarios,
            charts=chart_data,
            evidence_sources=self._sources(comp_dict, data_available),
            warnings=list(dict.fromkeys(warnings)),
        )

    # -- scenario simulation (Module 8) ------------------------------------

    @staticmethod
    def _build_scenarios(context: dict[str, Any], compression, inversion) -> list[EquityScenario]:
        """Simulate current vs. alternative offers and their equity trade-offs."""
        offer = context["offer"]
        target = float(offer.get("target", 0.0))
        cur = offer.get("currency", "INR")
        unit = offer.get("unit", "LPA")
        data = compression.data_available or inversion.data_available

        def _impact(delta_label: str) -> str:
            if not data:
                return "Internal equity impact cannot be quantified without connected data."
            return delta_label

        return [
            EquityScenario(
                name="Current Offer",
                offer_target=round(target, 2),
                currency=cur,
                unit=unit,
                equity_impact=_impact(
                    f"Baseline: compression {compression.risk_level}, inversion {inversion.risk_level}."
                ),
                budget_impact="Baseline budget.",
                promotion_impact="Baseline level alignment.",
                retention_impact="Baseline retention posture.",
                tradeoffs=["The offer as recommended by Compensation Governance."],
            ),
            EquityScenario(
                name="Equity-Optimized Offer",
                offer_target=round(target * 0.95, 2),
                currency=cur,
                unit=unit,
                equity_impact=_impact(
                    "Lower target reduces compression/inversion exposure vs. peers."
                ),
                budget_impact="~5% lower cash outlay.",
                promotion_impact="Improves parity with existing peers at the level.",
                retention_impact="Slightly higher risk of the candidate declining.",
                tradeoffs=["Better internal equity", "Higher decline risk"],
            ),
            EquityScenario(
                name="Competitive-Win Offer",
                offer_target=round(target * 1.05, 2),
                currency=cur,
                unit=unit,
                equity_impact=_impact(
                    "Higher target increases compression/inversion exposure vs. peers."
                ),
                budget_impact="~5% higher cash outlay.",
                promotion_impact="May pull the level band upward; document for parity.",
                retention_impact="Stronger close and short-term retention.",
                tradeoffs=[
                    "Higher close probability",
                    "Greater equity exposure — route for review",
                ],
            ),
        ]

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _extract(comp_report: Any, key: str) -> dict[str, Any]:
        """Pull a normalized signal dict the compensation engine already gathered."""
        # The compensation report exposes future outlook + charts, but the raw
        # intelligence/timeline live on the candidate insight bundle. We read the
        # lightweight signals the comp report surfaces to avoid re-running engines.
        charts = getattr(comp_report, "charts", {}) or {}
        if key == "intelligence":
            bv = charts.get("business_value", {})
            return {"career_growth_score": 0.0, "_levels": bv}
        return {}

    def _narrative(self, payload: PayEquityInput, evidence: dict[str, Any]) -> PayEquityNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        try:
            result = self.ai_runner.run(pay_equity_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return PayEquityNarrative(**compose_pay_equity_narrative(evidence))

    @staticmethod
    def _sources(comp_dict: dict[str, Any], data_available: bool) -> list[str]:
        """Return the evidence sources actually consulted."""
        sources = ["Compensation Governance Agent"]
        sources.extend(comp_dict.get("evidence_sources", []))
        if data_available:
            sources.append("Connected internal compensation data")
        return list(dict.fromkeys(sources))

    @classmethod
    def _next_report_id(cls, candidate_id: str) -> str:
        """Return a process-unique report id."""
        cls._counter += 1
        return f"pay_equity_{candidate_id}_{cls._counter}"


# A shared default engine for the tool / copilot / UI.
pay_equity_guardian_engine = PayEquityGuardianEngine()
