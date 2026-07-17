from pydantic import BaseModel


class HiringRecommendation(BaseModel):
    recommendation: str

    confidence: float

    fit_score: float

    reasons: list[str]

    concerns: list[str]

    interview_focus: list[str]

    estimated_offer_level: str

    estimated_salary_band: str
