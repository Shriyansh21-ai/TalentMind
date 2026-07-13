def experience_score(candidate):

    score = 0

    years = candidate.profile.years_of_experience

    score += min(years * 10, 60)

    score += min(len(candidate.career_history) * 5, 20)

    titles = [
        j.title.lower()
        for j in candidate.career_history
    ]

    senior_titles = [

        "senior",

        "lead",

        "principal",

        "staff",

        "architect"

    ]

    if any(
        t in " ".join(titles)
        for t in senior_titles
    ):

        score += 20

    return min(score,100)