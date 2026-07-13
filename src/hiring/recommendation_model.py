from pydantic import BaseModel
from typing import List


class HiringRecommendation(BaseModel):

    recommendation: str

    confidence: float

    fit_score: float

    reasons: List[str]

    concerns: List[str]

    interview_focus: List[str]

    estimated_offer_level: str

    estimated_salary_band: str