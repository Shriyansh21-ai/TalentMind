def interview_topics(candidate, gap):

    topics = []

    missing = gap["missing"]

    if "Python" in missing:
        topics.append("Advanced Python")

    if "AWS" in missing:
        topics.append("Cloud Architecture")

    if "Docker" in missing:
        topics.append("Containerization")

    if "LLM" in missing:
        topics.append("Generative AI Systems")

    if not topics:
        topics.append("System Design")

        topics.append("Leadership")

    return topics
