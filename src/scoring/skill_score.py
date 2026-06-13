from src.models.candidates import Candidate


TARGET_SKILLS = {
    "python",
    "embeddings",
    "retrieval",
    "ranking",
    "vector databases",
    "pinecone",
    "weaviate",
    "qdrant",
    "milvus",
    "faiss",
    "elasticsearch",
    "opensearch",
    "llm",
    "fine-tuning",
    "lora",
    "qlora",
    "peft",
    "evaluation",
    "ndcg",
    "mrr",
    "map"
}


def calculate_skill_score(candidate: Candidate):

    score = 0

    candidate_skills = {
        skill.name.lower()
        for skill in candidate.skills
    }

    for target in TARGET_SKILLS:

        if target in candidate_skills:
            score += 5

    return score