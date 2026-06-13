import faiss
import numpy as np

from src.semantic.embeddings import (
    get_embedding,
    candidate_text
)

index = None
candidate_store = []


def build_search_index(candidates):

    global index
    global candidate_store

    candidate_store = candidates

    vectors = []

    for candidate in candidates:

        vectors.append(
            get_embedding(
                candidate_text(candidate)
            )
        )

    vectors = np.array(
        vectors,
        dtype="float32"
    )

    dimension = vectors.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(vectors)


def recruiter_search(
    query,
    top_k=20
):

    global index
    global candidate_store

    query_vector = get_embedding(
        query
    )

    query_vector = np.array(
        [query_vector],
        dtype="float32"
    )

    scores, ids = index.search(
        query_vector,
        top_k
    )

    results = []

    for idx, score in zip(
        ids[0],
        scores[0]
    ):

        results.append(
            (
                candidate_store[idx],
                float(score)
            )
        )

    return results