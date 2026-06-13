def build_candidate_text(candidate):

    text = ""

    text += candidate.profile.summary + " "

    text += candidate.profile.current_title + " "

    for skill in candidate.skills:
        text += skill.name + " "

    for job in candidate.career_history:
        text += job.description + " "

    return text