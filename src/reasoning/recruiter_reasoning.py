from src.scoring.skill_score import calculate_skill_score
from src.scoring.experience_score import calculate_experience_score
from src.scoring.title_score import calculate_title_score
from src.scoring.behavior_score import calculate_behavior_score
from src.scoring.career_score import calculate_career_score
from src.scoring.jd_matcher import calculate_jd_match_score
from src.scoring.availability import calculate_availability_score
from src.scoring.red_flags import calculate_red_flag_penalty


def generate_recruiter_reason(candidate):

    reasons = []

    if calculate_skill_score(candidate) >= 25:
        reasons.append("Strong alignment with required AI/ML skills")

    if candidate.profile.years_of_experience >= 5:
        reasons.append(
            f"{candidate.profile.years_of_experience} years of relevant experience"
        )

    title = candidate.profile.current_title.lower()

    if any(
        keyword in title
        for keyword in [
            "ai",
            "ml",
            "machine learning",
            "nlp",
            "recommendation"
        ]
    ):
        reasons.append(
            f"Current role ({candidate.profile.current_title}) closely matches target position"
        )

    if calculate_career_score(candidate) >= 20:
        reasons.append(
            "Career history includes retrieval, ranking, recommendation or LLM projects"
        )

    if calculate_jd_match_score(candidate) >= 30:
        reasons.append(
            "Strong match with job requirements"
        )

    if calculate_behavior_score(candidate) >= 25:
        reasons.append(
            "Positive recruiter engagement signals"
        )

    if calculate_availability_score(candidate) >= 20:
        reasons.append(
            "Reasonable notice period"
        )

    if calculate_red_flag_penalty(candidate) < 0:
        reasons.append(
            "Some hiring risks detected"
        )

    return reasons