# src/recruiter/pipeline.py

import json
import os

FILE_PATH = "data/recruiter_actions.json"


def load_actions():

    if not os.path.exists(FILE_PATH):
        return {}

    with open(FILE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_status(candidate_id, status):

    data = load_actions()

    data[candidate_id] = status

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_status(candidate_id):

    data = load_actions()

    return data.get(candidate_id, "New")
