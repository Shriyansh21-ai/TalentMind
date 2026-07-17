# src/utils/analyzer.py

from collections import Counter


def analyze_dataset(candidates):

    print("=" * 60)
    print("DATASET OVERVIEW")
    print("=" * 60)

    print(f"Total Candidates: {len(candidates)}")

    countries = Counter(c.profile.country for c in candidates)

    print("\nTop Countries")

    for country, count in countries.most_common(10):
        print(country, count)

    skills = Counter()

    for candidate in candidates:
        for skill in candidate.skills:
            skills[skill.name] += 1

    print("\nTop Skills")

    for skill, count in skills.most_common(20):
        print(skill, count)
