"""Evaluation metrics for structured outputs."""


def schema_pass_rate(results: list[tuple[bool, list[str]]]) -> float:
    """Fraction of outputs that pass schema validation."""
    if not results:
        return 0.0
    return sum(1 for valid, _ in results if valid) / len(results)


def evidence_coverage_rate(outputs: list[dict]) -> float:
    """Fraction of outputs where all key fields have evidence quotes."""
    if not outputs:
        return 0.0
    required_fields = {"root_cause", "sentiment", "risk", "recommendation"}
    covered = 0
    for output in outputs:
        evidence_fields = {e["field"] for e in output.get("evidence", [])}
        if required_fields <= evidence_fields:
            covered += 1
    return covered / len(outputs)


def unsupported_claim_rate(outputs: list[dict]) -> float:
    """Fraction of outputs with recommendations that lack evidence."""
    if not outputs:
        return 0.0
    unsupported = 0
    for output in outputs:
        evidence_fields = {e["field"] for e in output.get("evidence", [])}
        if "recommendation" not in evidence_fields:
            unsupported += 1
    return unsupported / len(outputs)


def review_routing_precision_recall(
    predictions: list[bool], gold: list[bool]
) -> dict:
    """Compute precision and recall for review routing."""
    tp = sum(1 for p, g in zip(predictions, gold) if p and g)
    fp = sum(1 for p, g in zip(predictions, gold) if p and not g)
    fn = sum(1 for p, g in zip(predictions, gold) if not p and g)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return {"precision": precision, "recall": recall}
