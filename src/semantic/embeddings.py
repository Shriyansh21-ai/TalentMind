import streamlit as st
from sentence_transformers import SentenceTransformer


@st.cache_resource
def get_embedding_model():

    return SentenceTransformer("BAAI/bge-small-en-v1.5")


def candidate_text(candidate):

    text = candidate.profile.current_title + " " + candidate.profile.summary

    for job in candidate.career_history:
        text += " " + job.title
        text += " " + job.description

    return text


def get_embedding(text):

    model = get_embedding_model()

    return model.encode(text, normalize_embeddings=True)
