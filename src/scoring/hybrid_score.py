from src.scoring.final_score import calculate_final_score

from src.semantic.semantic_score import (
    calculate_semantic_score
)


def hybrid_score(candidate, job_profile):

    rule_score = calculate_final_score(candidate)

    semantic_score = calculate_semantic_score(
        candidate,
        job_profile.to_text()
    )

    return rule_score + semantic_score