"""Discussion round (Module 3).

After the independent reviews, the members "exchange findings". This phase
deterministically surfaces agreements, disagreements, evidence-backed challenges,
and missing evidence. Every challenge cites the evidence behind it — no member
challenges another without grounds, and nothing is fabricated.
"""

from __future__ import annotations

from src.ai.committee.schemas import DiscussionRound, MemberOpinion
from src.ai.committee.voting import stance_of

_ALL_SOURCES = {
    "Resume Analyst Agent",
    "JD Analyst Agent",
    "Candidate Intelligence engine",
    "Risk Intelligence",
    "Career Timeline Intelligence",
    "Interview Intelligence",
    "Hiring Recommendation engine",
}


def run_discussion(opinions: list[MemberOpinion]) -> DiscussionRound:
    """Facilitate the discussion round and return its structured output."""
    active = [o for o in opinions if not o.abstained]
    round_ = DiscussionRound()

    # Agreements: group members sharing a stance direction.
    positive = [o.role_title for o in active if stance_of(o.recommendation) > 0.4]
    negative = [o.role_title for o in active if stance_of(o.recommendation) < -0.4]
    neutral = [o.role_title for o in active if -0.4 <= stance_of(o.recommendation) <= 0.4]
    if len(positive) >= 2:
        round_.agreements.append("Lean-hire alignment: " + ", ".join(positive) + ".")
    if len(negative) >= 2:
        round_.agreements.append("Caution alignment: " + ", ".join(negative) + ".")
    if len(neutral) >= 2:
        round_.agreements.append("Hold/neutral alignment: " + ", ".join(neutral) + ".")

    # Disagreements: opposite directions co-existing.
    if positive and negative:
        round_.disagreements.append(
            f"Directional split — positive: {', '.join(positive)}; negative: {', '.join(negative)}."
        )

    # Challenges: a higher-confidence, better-evidenced member challenging a
    # divergent, weaker-evidenced member. Each challenge references evidence.
    round_.challenges = _build_challenges(active)

    # Missing evidence: which expected sources never contributed.
    present_sources = {s for o in opinions for s in o.evidence_sources if not o.abstained}
    absent = sorted(_ALL_SOURCES - present_sources)
    abstained = [o.role_title for o in opinions if o.abstained]
    for src in absent:
        round_.missing_evidence.append(f"No contribution from: {src}.")
    for title in abstained:
        round_.notes.append(f"{title} abstained (insufficient evidence).")

    if not round_.disagreements:
        round_.notes.append("No directional disagreement; members differ only in degree.")
    return round_


def _build_challenges(active: list[MemberOpinion]) -> list[dict[str, object]]:
    """Return evidence-backed challenges between divergent members."""
    challenges: list[dict[str, object]] = []
    for challenger in active:
        for target in active:
            if challenger.role == target.role:
                continue
            gap = stance_of(challenger.recommendation) - stance_of(target.recommendation)
            # A confident, well-evidenced member challenges a more-negative, less
            # confident member (or vice-versa) when they diverge materially.
            if (
                abs(gap) >= 2.0
                and challenger.confidence >= target.confidence + 10
                and challenger.evidence
            ):
                challenges.append(
                    {
                        "challenger": challenger.role_title,
                        "target": target.role_title,
                        "claim": (
                            f"{challenger.role_title} ({challenger.recommendation.value}) challenges "
                            f"{target.role_title} ({target.recommendation.value})."
                        ),
                        "evidence": challenger.evidence[0],
                        "confidence_gap": round(challenger.confidence - target.confidence, 1),
                    }
                )
    # Keep the most decisive few.
    challenges.sort(key=lambda c: c["confidence_gap"], reverse=True)
    return challenges[:4]
