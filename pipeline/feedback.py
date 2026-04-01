"""Human feedback storage: read/write corrections to feedback.jsonl.

Every human correction is appended as one JSON line. This creates an
immutable audit trail — corrections are never overwritten, only appended.
"""
import json
import time
from pathlib import Path

FEEDBACK_PATH = Path("data/processed/feedback.jsonl")


def save_feedback(
    case_id: str,
    original_extraction: dict,
    corrected_fields: dict,
    reviewer_notes: str = "",
) -> dict:
    """Append a human correction to feedback.jsonl.

    Args:
        case_id: The case being corrected
        original_extraction: The AI extraction output (before correction)
        corrected_fields: Dict of {field_name: corrected_value} — only changed fields
        reviewer_notes: Free-text notes from the reviewer

    Returns:
        The feedback entry that was written
    """
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.time(),
        "case_id": case_id,
        "action": "correction",
        "original": {k: original_extraction.get(k) for k in corrected_fields},
        "corrected": corrected_fields,
        "reviewer_notes": reviewer_notes,
        "agreement": _compute_field_agreement(original_extraction, corrected_fields),
    }

    with open(FEEDBACK_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def save_approval(case_id: str, extraction: dict, reviewer_notes: str = "") -> dict:
    """Record that a reviewer approved the AI output without changes."""
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": time.time(),
        "case_id": case_id,
        "action": "approval",
        "original": {},
        "corrected": {},
        "reviewer_notes": reviewer_notes,
        "agreement": {
            "fields_reviewed": _reviewable_fields(),
            "fields_agreed": _reviewable_fields(),
            "agreement_rate": 1.0,
        },
    }

    with open(FEEDBACK_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def load_all_feedback() -> list[dict]:
    """Load all feedback entries from feedback.jsonl."""
    if not FEEDBACK_PATH.exists():
        return []

    entries = []
    with open(FEEDBACK_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def compute_agreement_stats(feedback: list[dict] | None = None) -> dict:
    """Compute aggregate human-AI agreement statistics.

    Returns:
        {
            "total_reviews": int,
            "approvals": int,
            "corrections": int,
            "overall_agreement_rate": float,   # 0.0 to 1.0
            "per_field_agreement": {field: rate},
            "most_corrected_fields": [(field, count)],
        }
    """
    if feedback is None:
        feedback = load_all_feedback()

    if not feedback:
        return {
            "total_reviews": 0,
            "approvals": 0,
            "corrections": 0,
            "overall_agreement_rate": 0.0,
            "per_field_agreement": {},
            "most_corrected_fields": [],
        }

    total = len(feedback)
    approvals = sum(1 for f in feedback if f.get("action") == "approval")
    corrections = sum(1 for f in feedback if f.get("action") == "correction")

    # Per-field agreement
    field_agreed = {}
    field_total = {}
    for entry in feedback:
        if entry.get("action") == "approval":
            for field in _reviewable_fields():
                field_total[field] = field_total.get(field, 0) + 1
                field_agreed[field] = field_agreed.get(field, 0) + 1
        elif entry.get("action") == "correction":
            corrected = set(entry.get("corrected", {}).keys())
            for field in _reviewable_fields():
                field_total[field] = field_total.get(field, 0) + 1
                if field not in corrected:
                    field_agreed[field] = field_agreed.get(field, 0) + 1

    per_field = {
        field: field_agreed.get(field, 0) / field_total[field]
        for field in field_total
        if field_total[field] > 0
    }

    # Most corrected fields
    from collections import Counter
    correction_counts = Counter()
    for entry in feedback:
        if entry.get("action") == "correction":
            for field in entry.get("corrected", {}):
                correction_counts[field] += 1

    # Overall agreement rate: weighted by fields
    if field_total:
        total_agreed = sum(field_agreed.values())
        total_possible = sum(field_total.values())
        overall = total_agreed / total_possible if total_possible > 0 else 0.0
    else:
        overall = approvals / total if total > 0 else 0.0

    return {
        "total_reviews": total,
        "approvals": approvals,
        "corrections": corrections,
        "overall_agreement_rate": overall,
        "per_field_agreement": per_field,
        "most_corrected_fields": correction_counts.most_common(),
    }


def _reviewable_fields() -> list[str]:
    """Fields that a human reviewer can correct."""
    return [
        "root_cause_l1",
        "root_cause_l2",
        "sentiment_score",
        "risk_level",
        "confidence",
        "churn_risk",
        "review_required",
    ]


def _compute_field_agreement(original: dict, corrected: dict) -> dict:
    """Compute per-correction agreement info."""
    reviewable = _reviewable_fields()
    corrected_set = set(corrected.keys())
    agreed = [f for f in reviewable if f not in corrected_set]
    return {
        "fields_reviewed": reviewable,
        "fields_agreed": agreed,
        "fields_corrected": list(corrected_set),
        "agreement_rate": len(agreed) / len(reviewable) if reviewable else 1.0,
    }
