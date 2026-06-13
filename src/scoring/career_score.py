def calculate_career_score(candidate):

    score = 0

    strong_keywords = [
        "retrieval",
        "ranking",
        "recommendation",
        "recommendation system",
        "search",
        "vector",
        "embedding",
        "embeddings",
        "rag",
        "learning to rank",
        "reranking",
        "re-ranking"
    ]

    medium_keywords = [
        "llm",
        "nlp",
        "transformer",
        "fine tuning",
        "lora",
        "pinecone",
        "weaviate",
        "qdrant",
        "milvus",
        "faiss",
        "elasticsearch"
    ]

    for job in candidate.career_history:

        text = job.description.lower()

        for keyword in strong_keywords:
            if keyword in text:
                score += 8

        for keyword in medium_keywords:
            if keyword in text:
                score += 4

    return min(score, 30)