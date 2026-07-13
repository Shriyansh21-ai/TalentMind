def estimate_offer(candidate):

    years = candidate.profile.years_of_experience

    title = candidate.profile.current_title.lower()

    if "principal" in title:

        return "Principal AI Engineer"

    if "staff" in title:

        return "Staff AI Engineer"

    if "lead" in title:

        return "Lead AI Engineer"

    if "senior" in title:

        return "Senior AI Engineer"

    if years >= 5:

        return "Senior Engineer"

    return "Software Engineer"