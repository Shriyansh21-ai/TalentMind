def strengths(candidate):

    strengths = []

    skills = {s.name.lower() for s in candidate.skills}

    if "python" in skills:
        strengths.append("Strong Python expertise")

    if "llm" in skills:
        strengths.append("Production LLM experience")

    if "rag" in skills:
        strengths.append("Built Retrieval-Augmented systems")

    if candidate.profile.years_of_experience > 5:
        strengths.append("Experienced engineer")

    return strengths
