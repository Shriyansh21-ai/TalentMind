import re

from .keyword_extractor import extract_keywords
from .models import JobProfile
from .skill_classifier import classify


def parse_jd(text: str):

    # -------------------------
    # Role
    # -------------------------

    role_match = re.search(r"(Senior|Lead|Principal|Staff)?\s?.*Engineer", text, re.I)

    role = role_match.group(0) if role_match else "Unknown"

    # -------------------------
    # Experience
    # -------------------------

    exp = re.search(r"(\d+)\+?\s+years", text, re.I)

    experience = int(exp.group(1)) if exp else 0

    # -------------------------
    # Leadership
    # -------------------------

    leadership = "lead" in text.lower() or "mentor" in text.lower() or "manage" in text.lower()

    # -------------------------
    # Keywords
    # -------------------------

    keywords = extract_keywords(text)

    # -------------------------
    # Classify skills
    # -------------------------

    tech, soft, other = classify(keywords)

    # -------------------------
    # Return Job Profile
    # -------------------------

    return JobProfile(
        role=role,
        department="Engineering",
        industry="Technology",
        seniority="Senior",
        employment_type="Full Time",
        location="Not Specified",
        experience=experience,
        education="Bachelor",
        mandatory_skills=tech,
        preferred_skills=other,
        soft_skills=soft,
        technologies=tech,
        responsibilities=[],
        interview_focus=[],
        keywords=keywords,
        leadership_required=leadership,
        complexity_score=0,
        hiring_difficulty="Unknown",
    )
