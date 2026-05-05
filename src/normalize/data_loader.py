import json
import os
import csv


def load_dataset(path: str) -> list:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Dataset file not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".jsonl":
        return _load_jsonl(path)
    elif ext == ".json":
        return _load_json(path)
    elif ext == ".csv":
        return _load_csv(path)
    else:
        raise ValueError(f"Unsupported file extension '{ext}'. Use .json, .jsonl, or .csv")


def _load_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    raise ValueError("JSON file must contain a list or a dict with a 'data' key.")


def _load_jsonl(path: str) -> list:
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def _load_csv(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)
