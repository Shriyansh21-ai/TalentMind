from .career_growth import career_growth
from .confidence import confidence
from .experience import experience_score
from .hiring_risk import hiring_risk
from .leadership import leadership_score
from .learning_velocity import learning_velocity
from .models import CandidateIntelligence
from .strengths import strengths
from .technical import technical_score
from .weaknesses import weaknesses


def build_candidate_intelligence(candidate):

    exp = experience_score(candidate)

    tech = technical_score(candidate)

    leader = leadership_score(candidate)

    growth = career_growth(candidate)

    learning = learning_velocity(candidate)

    risk, risk_score = hiring_risk(candidate)

    conf = confidence(candidate)

    overall = round(exp * 0.25 + tech * 0.30 + leader * 0.15 + growth * 0.15 + learning * 0.15, 2)

    if overall > 85:
        recommendation = "Strong Hire"

    elif overall > 70:
        recommendation = "Hire"

    elif overall > 55:
        recommendation = "Hold"

    else:
        recommendation = "Reject"

    return CandidateIntelligence(
        candidate_id=candidate.candidate_id,
        overall_score=overall,
        experience_score=exp,
        technical_score=tech,
        leadership_score=leader,
        career_growth_score=growth,
        learning_velocity=learning,
        hiring_risk=risk,
        hiring_risk_score=risk_score,
        confidence=conf,
        strengths=strengths(candidate),
        weaknesses=weaknesses(candidate),
        recommendation=recommendation,
    )
