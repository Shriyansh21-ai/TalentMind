from src.models.candidates import Candidate


CONSULTING = {
    "tcs",
    "infosys",
    "wipro",
    "cognizant",
    "capgemini",
    "accenture"
}

def calculate_company_score(candidate):

    current = candidate.profile.current_company.lower()

    if current in CONSULTING:
        return -10

    return 5