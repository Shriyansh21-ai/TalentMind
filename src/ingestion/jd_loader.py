# src/ingestion/jd_loader.py

from pathlib import Path


def load_job_description(file_path: str):

    path = Path(file_path)

    with open(path, encoding="utf-8") as f:
        return f.read()
