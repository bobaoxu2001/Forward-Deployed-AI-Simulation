"""Data loaders for public datasets and case bundles."""
import json
from pathlib import Path


def load_case_bundle(path: str | Path) -> dict:
    """Load a single case bundle from JSON file."""
    with open(path) as f:
        return json.load(f)


def load_all_cases(cases_dir: str | Path) -> list[dict]:
    """Load all case bundles from a directory."""
    cases_dir = Path(cases_dir)
    cases = []
    for p in sorted(cases_dir.glob("*.json")):
        cases.append(load_case_bundle(p))
    return cases
