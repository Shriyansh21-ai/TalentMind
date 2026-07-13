from pydantic import BaseModel
from typing import List


class CandidateIntelligence(BaseModel):

    candidate_id: str

    overall_score: float

    experience_score: float

    technical_score: float

    leadership_score: float

    career_growth_score: float

    learning_velocity: float

    hiring_risk: str

    hiring_risk_score: float

    confidence: float

    strengths: List[str]

    weaknesses: List[str]

    recommendation: str