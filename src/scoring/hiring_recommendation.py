# src/scoring/hiring_recommendation.py


def get_hiring_recommendation(score, gap_percent, red_flags=0):

    if red_flags < 0:
        return ("❌ REJECT", "Candidate has risk indicators.")

    if score >= 90 and gap_percent >= 80:
        return ("🟢 STRONG HIRE", "Excellent match for the role.")

    if score >= 80 and gap_percent >= 70:
        return ("🟢 HIRE", "Strong candidate with good alignment.")

    if score >= 65:
        return ("🟡 MAYBE", "Requires recruiter review.")

    return ("🔴 REJECT", "Insufficient match.")
