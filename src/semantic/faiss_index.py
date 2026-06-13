import faiss
import numpy as np

from src.semantic.embeddings import (
    get_embedding,
    candidate_text
)


def build_faiss_index(candidates):

    vectors = []

    for candidate in candidates:

        embedding = get_embedding(
            candidate_text(candidate)
        )

        vectors.append(embedding)

    vectors = np.array(
        vectors,
        dtype="float32"
    )

    dimension = vectors.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(vectors)

    return index

def search_candidates(
    jd_text,
    candidates,
    index,
    top_k=200
):

    jd_embedding = get_embedding(
        jd_text
    )

    jd_embedding = np.array(
        [jd_embedding],
        dtype="float32"
    )

    scores, indices = index.search(
        jd_embedding,
        top_k
    )

    results = []

    for idx in indices[0]:

        results.append(
            candidates[idx]
        )

    return results