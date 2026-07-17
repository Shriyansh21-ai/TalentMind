def calculate_title_score(candidate):

    title = candidate.profile.current_title.lower()

    keywords = ["ai", "machine learning", "ml", "nlp", "retrieval", "ranking"]

    for word in keywords:
        if word in title:
            return 15

    return 0
