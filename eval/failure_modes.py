"""Failure mode detection and tagging."""

FAILURE_TYPES = [
    "hallucination",
    "omission",
    "overconfidence",
    "ambiguity",
    "language_format_drift",
    "spurious_correlation",
]


def detect_hallucination(output: dict) -> bool:
    """Check if any recommendation/attribution lacks evidence."""
    evidence_fields = {e["field"] for e in output.get("evidence", [])}
    return "recommendation" not in evidence_fields


def detect_omission(output: dict, case: dict) -> bool:
    """Placeholder: check if clear signals in input are missing from output."""
    # Will be implemented with keyword/pattern matching in Phase C
    return False


def detect_overconfidence(output: dict, gold_root_cause: str | None) -> bool:
    """High confidence but wrong root cause (requires gold label)."""
    if gold_root_cause is None:
        return False
    confidence = output.get("root_cause", {}).get("confidence", 0)
    predicted = output.get("root_cause", {}).get("l1", "")
    return confidence > 0.85 and predicted != gold_root_cause


def tag_failure_modes(output: dict, case: dict) -> list[str]:
    """Return list of failure mode tags for a given output."""
    tags = []
    if detect_hallucination(output):
        tags.append("hallucination")
    if detect_omission(output, case):
        tags.append("omission")
    gold = case.get("labels", {}).get("gold_root_cause")
    if detect_overconfidence(output, gold):
        tags.append("overconfidence")
    return tags
