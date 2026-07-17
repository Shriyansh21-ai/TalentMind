def hiring_risk(candidate):

    risk = 0

    if candidate.redrob_signals.notice_period_days > 60:
        risk += 30

    if len(candidate.career_history) > 6:
        risk += 20

    if candidate.profile.years_of_experience < 2:
        risk += 20

    if risk < 30:
        return "Low", risk

    elif risk < 60:
        return "Medium", risk

    return "High", risk
