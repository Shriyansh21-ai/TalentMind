TECH = {

"Python",
"Java",
"C++",
"TensorFlow",
"PyTorch",
"AWS",
"GCP",
"Azure",
"Docker",
"Kubernetes",
"LangChain",
"RAG",
"LLM",
"SQL",
"FAISS"

}

SOFT = {

"Leadership",
"Communication",
"Problem Solving",
"Ownership",
"Mentoring",
"Teamwork"

}


def classify(skills):

    tech=[]

    soft=[]

    other=[]

    for skill in skills:

        if skill in TECH:

            tech.append(skill)

        elif skill in SOFT:

            soft.append(skill)

        else:

            other.append(skill)

    return tech,soft,other