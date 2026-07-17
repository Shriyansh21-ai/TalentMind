from .interview_focus import interview_topics
from .offer_prediction import estimate_offer
from .recommendation_model import HiringRecommendation
from .salary_band import estimate_salary


def generate_hiring_recommendation(candidate, intelligence, gap):

    reasons = []

    concerns = []

    score = intelligence.overall_score

    # -------------------------
    # Positive Signals
    # -------------------------

    if intelligence.technical_score > 80:
        reasons.append("Strong technical capability.")

    if intelligence.experience_score > 80:
        reasons.append("Relevant industry experience.")

    if intelligence.leadership_score > 70:
        reasons.append("Leadership and ownership experience.")

    if gap["match_percent"] > 75:
        reasons.append("Excellent alignment with JD.")

    # -------------------------
    # Concerns
    # -------------------------

    if gap["match_percent"] < 60:
        concerns.append("Important skills are missing.")

    if intelligence.hiring_risk == "High":
        concerns.append("High hiring risk detected.")

    if intelligence.learning_velocity < 50:
        concerns.append("Slow technology adoption.")

    # -------------------------
    # Recommendation
    # -------------------------

    if score >= 90:
        recommendation = "★★★★★ Strong Hire"

    elif score >= 75:
        recommendation = "★★★★☆ Hire"

    elif score >= 60:
        recommendation = "★★★☆☆ Hold"

    else:
        recommendation = "★☆☆☆☆ Reject"

    confidence = round(score * 0.95, 1)

    offer = estimate_offer(candidate)

    salary = estimate_salary(candidate)

    interview = interview_topics(candidate, gap)

    return HiringRecommendation(
        recommendation=recommendation,
        confidence=confidence,
        fit_score=score,
        reasons=reasons,
        concerns=concerns,
        interview_focus=interview,
        estimated_offer_level=offer,
        estimated_salary_band=salary,
    )
