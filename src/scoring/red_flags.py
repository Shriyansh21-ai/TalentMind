def calculate_red_flag_penalty(candidate):

    penalty = 0

    title = candidate.profile.current_title.lower()

    bad_titles = [
        "marketing",
        "operations",
        "customer support",
        "sales",
        "hr",
        "recruiter"
    ]

    for bad in bad_titles:
        if bad in title:
            penalty -= 50

    return penalty