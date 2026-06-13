from sentence_transformers import CrossEncoder

model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank_candidates(
    jd,
    candidates
):

    pairs = []

    for candidate in candidates:

        text = (
            candidate.profile.summary
        )

        pairs.append(
            [jd, text]
        )

    scores = model.predict(
        pairs
    )

    results = []

    for candidate, score in zip(
        candidates,
        scores
    ):

        results.append(
            (
                candidate,
                float(score)
            )
        )

    results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return results