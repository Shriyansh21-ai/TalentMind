MODERN = {

"llm",

"rag",

"langchain",

"vector",

"agents",

"faiss",

"transformers",

"pytorch"

}

def learning_velocity(candidate):

    skills = {

        s.name.lower()

        for s in candidate.skills

    }

    modern = len(

        skills & MODERN

    )

    return min(

        modern * 12,

        100

    )