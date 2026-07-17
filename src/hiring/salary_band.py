def estimate_salary(candidate):

    years = candidate.profile.years_of_experience

    if years >= 12:
        return "$220k - $300k"

    if years >= 8:
        return "$170k - $220k"

    if years >= 5:
        return "$120k - $170k"

    return "$70k - $120k"
