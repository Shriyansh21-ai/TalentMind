WORDS = [

"lead",

"mentor",

"architect",

"manage",

"ownership",

"principal",

"staff"

]

def leadership_score(candidate):

    text = ""

    for job in candidate.career_history:

        text += job.title

        text += job.description

    text = text.lower()

    score = 0

    for word in WORDS:

        if word in text:

            score += 15

    return min(score,100)