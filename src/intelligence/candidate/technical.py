AI_SKILLS = {
    "python",
    "pytorch",
    "tensorflow",
    "llm",
    "langchain",
    "rag",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "sql",
    "faiss",
}


def technical_score(candidate):

    skills = {s.name.lower() for s in candidate.skills}

    matched = len(skills & AI_SKILLS)

    return min(matched * 8, 100)
