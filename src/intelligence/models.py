from pydantic import BaseModel


class JobProfile(BaseModel):
    role: str

    department: str

    industry: str

    seniority: str

    employment_type: str

    location: str

    experience: int

    education: str

    mandatory_skills: list[str]

    preferred_skills: list[str]

    soft_skills: list[str]

    technologies: list[str]

    responsibilities: list[str]

    interview_focus: list[str]

    keywords: list[str]

    leadership_required: bool

    complexity_score: float

    hiring_difficulty: str

    def to_text(self):

        return f"""
        Role: {self.role}

        Experience: {self.experience}

        Mandatory Skills:
        {" ".join(self.mandatory_skills)}

        Preferred Skills:
        {" ".join(self.preferred_skills)}

        Technologies:
        {" ".join(self.technologies)}
        """
