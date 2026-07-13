def analyze(profile):

    score=0

    score+=len(profile.mandatory_skills)*5

    score+=len(profile.preferred_skills)*2

    score+=profile.experience*2

    if profile.leadership_required:

        score+=15

    score=min(score,100)

    if score<35:

        difficulty="Easy"

    elif score<70:

        difficulty="Medium"

    else:

        difficulty="Hard"

    profile.complexity_score=score

    profile.hiring_difficulty=difficulty

    return profile