# src/llm/recruiter_summary.py


def generate_summary(candidate, explanation, skill_gap):

    summary = []

    summary.append(
        f"{candidate.profile.current_title} with "
        f"{candidate.profile.years_of_experience} years of experience."
    )

    summary.append(f"Matches {skill_gap['match_percent']}% of JD skills.")

    if len(skill_gap["missing"]) == 0:
        summary.append("All critical JD skills are present.")

    elif len(skill_gap["missing"]) <= 2:
        summary.append("Only minor skill gaps detected.")

    else:
        summary.append(f"Missing {len(skill_gap['missing'])} important JD skills.")

    if explanation["career_score"] >= 20:
        summary.append(
            "Has proven experience in retrieval, ranking, recommendation systems or LLM applications."
        )

    if explanation["experience_score"] >= 15:
        summary.append("Experience level aligns well with role expectations.")

    return summary
