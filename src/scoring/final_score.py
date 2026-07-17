from .availability import calculate_availability_score
from .behavior_score import calculate_behavior_score
from .career_score import calculate_career_score
from .company_score import calculate_company_score
from .experience_score import calculate_experience_score
from .jd_matcher import calculate_jd_match_score
from .penalty_score import calculate_penalty_score
from .red_flags import calculate_red_flag_penalty
from .skill_score import calculate_skill_score
from .title_score import calculate_title_score


def calculate_final_score(candidate):

    score = 0

    score += calculate_skill_score(candidate)
    score += calculate_experience_score(candidate)
    score += calculate_title_score(candidate)
    score += calculate_behavior_score(candidate)
    score += calculate_company_score(candidate)
    score += calculate_career_score(candidate)
    score += calculate_penalty_score(candidate)
    score += calculate_jd_match_score(candidate)
    score += calculate_availability_score(candidate)
    score += calculate_red_flag_penalty(candidate)

    return round(score, 2)
