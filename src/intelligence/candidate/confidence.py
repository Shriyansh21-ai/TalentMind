def confidence(candidate):

    score = 60

    if candidate.profile.summary:

        score += 10

    if candidate.skills:

        score += 10

    if candidate.career_history:

        score += 10

    if len(candidate.career_history)>2:

        score +=10

    return min(score,100)