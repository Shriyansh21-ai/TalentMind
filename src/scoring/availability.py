def calculate_availability_score(candidate):

    signals = candidate.redrob_signals

    score = 0

    if signals.open_to_work_flag:
        score += 10

    if signals.recruiter_response_rate > 0.7:
        score += 10
    elif signals.recruiter_response_rate > 0.5:
        score += 5

    if signals.notice_period_days <= 30:
        score += 10
    elif signals.notice_period_days <= 60:
        score += 5

    return score