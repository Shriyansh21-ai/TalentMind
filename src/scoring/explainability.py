from .skill_score import calculate_skill_score
from .experience_score import calculate_experience_score
from .title_score import calculate_title_score
from .behavior_score import calculate_behavior_score
from .company_score import calculate_company_score
from .career_score import calculate_career_score
from .penalty_score import calculate_penalty_score
from .jd_matcher import calculate_jd_match_score
from .availability import calculate_availability_score
from .red_flags import calculate_red_flag_penalty
from src.reasoning.recruiter_reasoning import generate_recruiter_reason

from .final_score import calculate_final_score
from src.scoring.skill_gap import (
    get_skill_gap
)


def explain_candidate(candidate):

    skill_score = calculate_skill_score(candidate)
    experience_score = calculate_experience_score(candidate)
    title_score = calculate_title_score(candidate)
    behavior_score = calculate_behavior_score(candidate)
    company_score = calculate_company_score(candidate)
    career_score = calculate_career_score(candidate)
    jd_match_score = calculate_jd_match_score(candidate)
    availability_score = calculate_availability_score(candidate)
    penalty_score = calculate_penalty_score(candidate)
    red_flag_penalty = calculate_red_flag_penalty(candidate)
    reasons = generate_recruiter_reason(candidate)
    gap = get_skill_gap(
    candidate,
    
)

    return {
    "candidate_id": candidate.candidate_id,
    "title": candidate.profile.current_title,
    "company": candidate.profile.current_company,

    "skill_score": skill_score,
    "experience_score": experience_score,
    "title_score": title_score,
    "behavior_score": behavior_score,
    "company_score": company_score,
    "career_score": career_score,

    "jd_match_score": jd_match_score,
    "availability_score": availability_score,

    "penalty_score": penalty_score,
    "red_flag_penalty": red_flag_penalty,

    "reasons": reasons,
    "skill_match_percent":
    gap["match_percent"],

    "matched_skills":
        gap["matched"],

    "missing_skills":
        gap["missing"],

    "total_score": round(
        calculate_final_score(candidate),
        2
    )
}