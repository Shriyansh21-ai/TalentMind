from src.semantic.embeddings import (
    candidate_text,
    get_embedding
)

import numpy as np


def find_similar_candidates(
    candidate,
    candidates,
    index,
    top_k=20
):

    embedding = get_embedding(
        candidate_text(candidate)
    )

    embedding = np.array(
        [embedding],
        dtype="float32"
    )

    scores, indices = index.search(
        embedding,
        top_k + 1
    )

    results = []

    for idx in indices[0]:

        if (
            candidates[idx].candidate_id
            != candidate.candidate_id
        ):
            results.append(
                candidates[idx]
            )

    return results[:top_k]