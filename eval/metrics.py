"""Evaluation metrics for the extraction pipeline.

All metrics operate on lists of (case_dict, extraction_dict) pairs
or on validation results, so they work whether you run batch eval
from files or from the database.
"""
from collections import Counter

from pipeline.validate import validate_extraction, check_evidence_present
from pipeline.gate import compute_gate_decision


# --- Core metrics ---

def schema_pass_rate(extractions: list[dict]) -> float:
    """Fraction of extractions that pass EXTRACTION_SCHEMA validation.

    Target: >= 0.98
    """
    if not extractions:
        return 0.0
    passed = sum(1 for e in extractions if validate_extraction(e)[0])
    return passed / len(extractions)


def evidence_coverage_rate(extractions: list[dict]) -> float:
    """Fraction of extractions with non-empty, non-blank evidence quotes.

    Target: >= 0.90
    """
    if not extractions:
        return 0.0
    covered = sum(1 for e in extractions if check_evidence_present(e)[0])
    return covered / len(extractions)


def review_required_rate(extractions: list[dict]) -> float:
    """Fraction of extractions routed to human review by the gate."""
    if not extractions:
        return 0.0
    reviewed = sum(
        1 for e in extractions if compute_gate_decision(e)["route"] == "review"
    )
    return reviewed / len(extractions)


def unsupported_recommendation_rate(extractions: list[dict]) -> float:
    """Fraction of extractions where next_best_actions exist but evidence is empty.

    An unsupported recommendation = has actions but no evidence quotes.
    Target: <= 0.02
    """
    if not extractions:
        return 0.0
    unsupported = 0
    for e in extractions:
        has_actions = bool(e.get("next_best_actions"))
        has_evidence = check_evidence_present(e)[0]
        if has_actions and not has_evidence:
            unsupported += 1
    return unsupported / len(extractions)


def root_cause_consistency(extractions: list[dict], cases: list[dict]) -> float:
    """Measure consistency: do similar tickets get the same root_cause_l1?

    Groups cases by source_dataset, then checks if cases from the same source
    cluster on the same root_cause_l1. Returns the average within-group
    agreement rate (fraction of cases matching the group's majority label).

    This is a proxy for consistency — perfect consistency = 1.0.
    Target: >= 0.70
    """
    if not extractions or not cases:
        return 0.0

    # Build a mapping: case_id -> root_cause_l1
    case_id_to_rc = {}
    for e in extractions:
        case_id = e.get("case_id", "")
        rc = e.get("root_cause_l1", "unknown")
        if case_id:
            case_id_to_rc[case_id] = rc

    # Group by source_dataset
    groups: dict[str, list[str]] = {}
    for c in cases:
        source = c.get("source_dataset", "unknown")
        case_id = c.get("case_id", "")
        if case_id in case_id_to_rc:
            groups.setdefault(source, []).append(case_id_to_rc[case_id])

    if not groups:
        return 0.0

    # For each group, compute agreement with majority label
    total_agreement = 0.0
    total_groups = 0
    for source, labels in groups.items():
        if len(labels) < 2:
            continue
        counter = Counter(labels)
        majority_count = counter.most_common(1)[0][1]
        agreement = majority_count / len(labels)
        total_agreement += agreement
        total_groups += 1

    if total_groups == 0:
        return 1.0  # Only singleton groups — trivially consistent

    return total_agreement / total_groups


def review_routing_precision_recall(
    predicted_review: list[bool],
    gold_review: list[bool],
) -> dict:
    """Precision and recall for review routing against gold labels.

    Target: precision >= 0.80, recall >= 0.90
    """
    if not predicted_review or not gold_review:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = sum(1 for p, g in zip(predicted_review, gold_review) if p and g)
    fp = sum(1 for p, g in zip(predicted_review, gold_review) if p and not g)
    fn = sum(1 for p, g in zip(predicted_review, gold_review) if not p and g)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {"precision": precision, "recall": recall, "f1": f1}


# --- Aggregate all metrics ---

def compute_all_metrics(
    extractions: list[dict],
    cases: list[dict] | None = None,
) -> dict:
    """Compute all evaluation metrics.

    Returns a dict with all metric names and values, plus pass/fail
    against target thresholds.
    """
    targets = {
        "schema_pass_rate": 0.98,
        "evidence_coverage_rate": 0.90,
        "unsupported_recommendation_rate": 0.02,  # upper bound
        "root_cause_consistency": 0.70,
    }

    spr = schema_pass_rate(extractions)
    ecr = evidence_coverage_rate(extractions)
    rrr = review_required_rate(extractions)
    urr = unsupported_recommendation_rate(extractions)
    rcc = root_cause_consistency(extractions, cases or [])

    metrics = {
        "schema_pass_rate": {"value": spr, "target": targets["schema_pass_rate"], "pass": spr >= targets["schema_pass_rate"]},
        "evidence_coverage_rate": {"value": ecr, "target": targets["evidence_coverage_rate"], "pass": ecr >= targets["evidence_coverage_rate"]},
        "review_required_rate": {"value": rrr, "target": None, "pass": None},  # no fixed target — informational
        "unsupported_recommendation_rate": {"value": urr, "target": targets["unsupported_recommendation_rate"], "pass": urr <= targets["unsupported_recommendation_rate"]},
        "root_cause_consistency": {"value": rcc, "target": targets["root_cause_consistency"], "pass": rcc >= targets["root_cause_consistency"]},
        "total_cases": len(extractions),
    }

    return metrics
