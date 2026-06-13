from sentence_transformers import util

from .embedding_model import model
from .text_builder import build_candidate_text


def calculate_semantic_score(
    candidate,
    jd_text
):

    candidate_text = build_candidate_text(
        candidate
    )

    jd_embedding = model.encode(
        jd_text,
        convert_to_tensor=True
    )

    candidate_embedding = model.encode(
        candidate_text,
        convert_to_tensor=True
    )

    similarity = util.cos_sim(
        jd_embedding,
        candidate_embedding
    )

    return float(similarity[0][0]) * 100