def calculate_jd_match_score(candidate):

    score = 0

    text = candidate.profile.summary.lower() + " " + candidate.profile.current_title.lower()

    for job in candidate.career_history:
        text += " " + job.description.lower()

    keywords = {
        "retrieval": 10,
        "ranking": 10,
        "recommendation": 12,
        "recommendation system": 15,
        "search": 8,
        "embeddings": 10,
        "embedding": 10,
        "vector": 8,
        "vector database": 12,
        "pinecone": 12,
        "weaviate": 12,
        "qdrant": 12,
        "milvus": 12,
        "faiss": 12,
        "bm25": 10,
        "hybrid retrieval": 15,
        "hybrid search": 15,
        "llm": 10,
        "rag": 15,
        "fine-tuning": 12,
        "lora": 10,
        "qlora": 10,
        "learning-to-rank": 15,
        "ndcg": 10,
        "mrr": 10,
        "map": 10,
        "a/b test": 10,
        "evaluation framework": 12,
    }

    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight

    return min(score, 60)
