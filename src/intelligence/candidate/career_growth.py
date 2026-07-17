LEVELS = {
    "intern": 1,
    "junior": 2,
    "engineer": 3,
    "senior": 4,
    "lead": 5,
    "principal": 6,
    "staff": 7,
}


def career_growth(candidate):

    history = []

    for job in candidate.career_history:
        title = job.title.lower()

        value = 0

        for level in LEVELS:
            if level in title:
                value = LEVELS[level]

        history.append(value)

    if not history:
        return 0

    growth = max(history) - min(history)

    return min(growth * 20, 100)
