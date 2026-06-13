from src.models.candidates import Candidate


def calculate_experience_score(candidate):

    exp = candidate.profile.years_of_experience

    if 5 <= exp <= 9:
        return 20

    elif 4 <= exp <= 12:
        return 10

    return 0