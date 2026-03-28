"""Data loaders for case bundles and raw datasets."""
import csv
import json
from pathlib import Path

import jsonschema

from pipeline.schemas import CaseBundle, CASE_SCHEMA


def load_case_bundle(path: str | Path) -> CaseBundle:
    """Load a single case bundle from JSON file and validate."""
    with open(path) as f:
        data = json.load(f)
    validate_case_dict(data)
    return CaseBundle.from_dict(data)


def load_all_cases(cases_dir: str | Path) -> list[CaseBundle]:
    """Load all case bundles from a directory."""
    cases_dir = Path(cases_dir)
    if not cases_dir.exists():
        raise FileNotFoundError(f"Cases directory not found: {cases_dir}")
    cases = []
    for p in sorted(cases_dir.glob("*.json")):
        cases.append(load_case_bundle(p))
    return cases


def save_case_bundle(case: CaseBundle, output_dir: str | Path) -> Path:
    """Save a case bundle as JSON file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{case.case_id}.json"
    data = case.to_dict()
    validate_case_dict(data)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def validate_case_dict(data: dict) -> None:
    """Validate a case dict against CASE_SCHEMA. Raises on failure."""
    jsonschema.validate(instance=data, schema=CASE_SCHEMA)


def load_csv_rows(path: str | Path) -> list[dict]:
    """Load rows from a CSV file as list of dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_jsonl(path: str | Path) -> list[dict]:
    """Load rows from a JSONL file."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
