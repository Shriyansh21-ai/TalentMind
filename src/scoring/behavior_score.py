def calculate_behavior_score(candidate):

    signals = candidate.redrob_signals

    score = 0

    if signals.open_to_work_flag:
        score += 10

    score += signals.recruiter_response_rate * 10

    score += signals.interview_completion_rate * 10

    if signals.notice_period_days <= 30:
        score += 10

    if signals.willing_to_relocate:
        score += 5

    return score
