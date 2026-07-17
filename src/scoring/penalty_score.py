def calculate_penalty_score(candidate):

    penalty = 0

    bad_companies = ["tcs", "infosys", "wipro", "accenture", "capgemini", "cognizant"]

    company = candidate.profile.current_company.lower()

    if company in bad_companies:
        penalty -= 15

    return penalty
