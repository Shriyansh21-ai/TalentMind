from pydantic import BaseModel
from typing import List


class JobProfile(BaseModel):

    role: str

    department: str

    industry: str

    seniority: str

    employment_type: str

    location: str

    experience: int

    education: str

    mandatory_skills: List[str]

    preferred_skills: List[str]

    soft_skills: List[str]

    technologies: List[str]

    responsibilities: List[str]

    interview_focus: List[str]

    keywords: List[str]

    leadership_required: bool

    complexity_score: float

    hiring_difficulty: str

    def to_text(self):

        return f"""
        Role: {self.role}

        Experience: {self.experience}

        Mandatory Skills:
        {' '.join(self.mandatory_skills)}

        Preferred Skills:
        {' '.join(self.preferred_skills)}

        Technologies:
        {' '.join(self.technologies)}
        """