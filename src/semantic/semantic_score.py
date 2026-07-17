from sentence_transformers import util

from .embeddings import get_embedding_model
from .text_builder import build_candidate_text


def calculate_semantic_score(candidate, jd_text):

    model = get_embedding_model()

    candidate_text = build_candidate_text(candidate)

    jd_embedding = model.encode(jd_text, convert_to_tensor=True, normalize_embeddings=True)

    candidate_embedding = model.encode(
        candidate_text, convert_to_tensor=True, normalize_embeddings=True
    )

    similarity = util.cos_sim(jd_embedding, candidate_embedding)

    return float(similarity[0][0]) * 100
