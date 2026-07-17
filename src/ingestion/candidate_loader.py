# src/ingestion/candidate_loader.py

import json
from pathlib import Path

from src.models.candidates import Candidate


def load_candidates(file_path: str):

    candidates = []

    path = Path(file_path)

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)

                candidate = Candidate(**row)

                candidates.append(candidate)

            except Exception as e:
                print(f"Error parsing candidate: {e}")

    return candidates
