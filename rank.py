# rank.py

import json

import pandas as pd

from src.ingestion.candidate_loader import load_candidates
from src.ingestion.jd_loader import load_job_description
from src.intelligence.jd_analyzer import analyze
from src.intelligence.jd_parser import parse_jd
from src.scoring.explainability import explain_candidate
from src.scoring.hybrid_score import hybrid_score
from src.semantic.faiss_index import build_faiss_index, search_candidates
from src.utils.analyzer import analyze_dataset


def main():

    print("\nLoading Job Description...")

    jd = load_job_description("data/raw/job_description.txt")

    print("JD Loaded")
    print(f"JD Length: {len(jd)} chars")

    # hybrid_score() consumes a parsed JobProfile (it calls job_profile.to_text()),
    # so build one here exactly as app.py does. FAISS retrieval below still uses the
    # raw JD text.
    job_profile = analyze(parse_jd(jd))

    print("\nLoading Candidates...")

    candidates = load_candidates("data/raw/candidates.jsonl")

    print(f"Candidates Loaded: {len(candidates)}")

    # Dataset statistics
    analyze_dataset(candidates)

    print("\nRunning Rule-Based Ranking...")

    print("\nBuilding FAISS Index...")

    index = build_faiss_index(candidates)

    print("FAISS Ready")

    print("\nSearching Candidates...")

    top_candidates = search_candidates(jd, candidates, index, top_k=500)

    print(f"Retrieved {len(top_candidates)} candidates")

    print("Running Semantic Ranking...")

    semantic_ranked = sorted(
        top_candidates, key=lambda c: hybrid_score(c, job_profile), reverse=True
    )

    print("\nTOP 10 CANDIDATES\n")

    for candidate in semantic_ranked[:10]:
        print(
            candidate.candidate_id,
            candidate.profile.current_title,
            round(hybrid_score(candidate, job_profile), 2),
        )

    print("\nTOP 5 EXPLANATIONS\n")

    for candidate in semantic_ranked[:5]:
        explanation = explain_candidate(candidate)

        print("\nCandidate:", explanation["candidate_id"])
        print("Title:", explanation["title"])
        print("Company:", explanation["company"])
        print("Score:", explanation["total_score"])

        print("\nReasons:")

        for reason in explanation["reasons"]:
            print("•", reason)

        print("-" * 60)

    top_100 = []

    for candidate in semantic_ranked[:100]:
        explanation = explain_candidate(candidate)

        explanation["hybrid_score"] = round(hybrid_score(candidate, job_profile), 2)

        top_100.append(explanation)

    with open("outputs/top_100_candidates.json", "w", encoding="utf-8") as f:
        json.dump(top_100, f, indent=4)

    top = semantic_ranked[0]

    print("\nTOP CANDIDATE")

    print(top.profile.current_title)
    print(top.profile.current_company)
    print(top.profile.years_of_experience)

    for job in top.career_history:
        print("\nJOB TITLE:", job.title)
        print(job.description[:300])

    df = pd.DataFrame(top_100)

    df.to_csv("outputs/top_100_candidates.csv", index=False)

    print("\nCSV Exported -> outputs/top_100_candidates.csv")


if __name__ == "__main__":
    main()
