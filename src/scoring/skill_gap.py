def get_skill_gap(candidate, jd_text):

    jd_text = jd_text.lower()

    candidate_skills = set()

    for skill in candidate.skills:

        candidate_skills.add(
            skill.name.lower()
        )

    important_skills = [
        "python",
        "machine learning",
        "deep learning",
        "nlp",
        "llm",
        "rag",
        "langchain",
        "transformers",
        "vector database",
        "faiss",
        "pinecone",
        "airflow",
        "mlflow",
        "kubeflow",
        "aws",
        "docker",
        "kubernetes",
        "tensorflow",
        "pytorch"
    ]

    required_skills = []

    for skill in important_skills:

        if skill in jd_text:
            required_skills.append(skill)

    matched_skills = []

    missing_skills = []

    for skill in required_skills:

        if skill in candidate_skills:

            matched_skills.append(skill)

        else:

            missing_skills.append(skill)

    return {
        "matched": matched_skills,
        "missing": missing_skills,
        "match_percent": round(
            (
                len(matched_skills)
                /
                max(len(required_skills), 1)
            ) * 100,
            2
        )
    }