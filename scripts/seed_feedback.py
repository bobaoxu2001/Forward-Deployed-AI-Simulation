"""Seed realistic human feedback data for demo purposes.

Simulates a reviewer going through 15 cases: approving some, correcting others.
Creates the feedback.jsonl that powers the Human Feedback analytics page.
"""
import json
import sqlite3
import time
import random
from pathlib import Path

FEEDBACK_PATH = Path("data/processed/feedback.jsonl")
DB_PATH = Path("data/processed/results.db")

random.seed(42)  # reproducible


def seed_feedback():
    """Generate 15 realistic feedback entries from actual pipeline extractions."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    extractions = [dict(r) for r in conn.execute("SELECT * FROM extractions").fetchall()]
    cases = {dict(r)["case_id"]: dict(r) for r in conn.execute("SELECT * FROM cases").fetchall()}
    conn.close()

    if not extractions:
        print("No extractions in DB. Run pipeline first.")
        return

    # Pick 15 cases: mix of review-routed and auto-routed
    review_cases = [e for e in extractions if e["gate_route"] == "review"]
    auto_cases = [e for e in extractions if e["gate_route"] == "auto"]

    selected = random.sample(review_cases, min(10, len(review_cases)))
    selected += random.sample(auto_cases, min(5, len(auto_cases)))
    random.shuffle(selected)

    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Clear existing
    FEEDBACK_PATH.write_text("")

    reviewable_fields = [
        "root_cause_l1", "root_cause_l2", "sentiment_score",
        "risk_level", "confidence", "churn_risk", "review_required",
    ]

    # Correction scenarios — realistic reviewer behavior
    correction_templates = [
        {
            "corrected": {"root_cause_l1": "billing", "root_cause_l2": "billing_dispute"},
            "notes": "AI classified as data_loss but this is clearly a billing dispute about charges",
        },
        {
            "corrected": {"risk_level": "high"},
            "notes": "Risk underestimated — customer mentioned legal action, should be high",
        },
        {
            "corrected": {"confidence": 0.5},
            "notes": "Text is too short and ambiguous for this confidence level. Lowered.",
        },
        {
            "corrected": {"root_cause_l1": "network", "risk_level": "medium"},
            "notes": "Misclassified as outage but it's a network performance issue, not full outage",
        },
        {
            "corrected": {"churn_risk": 0.8, "review_required": True},
            "notes": "VIP customer explicitly threatening to leave. Churn risk should be much higher.",
        },
    ]

    entries = []
    base_time = time.time() - 86400 * 3  # start 3 days ago

    for i, ext in enumerate(selected):
        ts = base_time + i * 3600 * random.uniform(2, 8)  # spread across days
        case_id = ext["case_id"]
        case_meta = cases.get(case_id, {})

        if i < 8:
            # First 8: approve (good AI output)
            entry = {
                "timestamp": ts,
                "case_id": case_id,
                "action": "approval",
                "original": {},
                "corrected": {},
                "reviewer_notes": random.choice([
                    "Classification looks correct.",
                    "Agree with AI assessment. Evidence is solid.",
                    "Good extraction. Risk level matches my read.",
                    "Verified — root cause and sentiment are accurate.",
                    "Approved. Evidence quotes are all grounded in source text.",
                    "Correct classification. No changes needed.",
                    "AI got this right. Good confidence calibration.",
                    "Looks good. Next actions are appropriate.",
                ]),
                "agreement": {
                    "fields_reviewed": reviewable_fields,
                    "fields_agreed": reviewable_fields,
                    "agreement_rate": 1.0,
                },
            }
        else:
            # Last 7: correct (AI made mistakes)
            template = correction_templates[(i - 8) % len(correction_templates)]
            corrected = template["corrected"]
            original = {k: ext.get(k) for k in corrected}
            agreed = [f for f in reviewable_fields if f not in corrected]

            entry = {
                "timestamp": ts,
                "case_id": case_id,
                "action": "correction",
                "original": original,
                "corrected": corrected,
                "reviewer_notes": template["notes"],
                "agreement": {
                    "fields_reviewed": reviewable_fields,
                    "fields_agreed": agreed,
                    "fields_corrected": list(corrected.keys()),
                    "agreement_rate": len(agreed) / len(reviewable_fields),
                },
            }

        entries.append(entry)

    with open(FEEDBACK_PATH, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    approvals = sum(1 for e in entries if e["action"] == "approval")
    corrections = len(entries) - approvals
    total_fields = len(entries) * len(reviewable_fields)
    agreed_fields = sum(
        len(e["agreement"].get("fields_agreed", reviewable_fields))
        for e in entries
    )
    rate = agreed_fields / total_fields if total_fields else 0

    print(f"Seeded {len(entries)} feedback entries to {FEEDBACK_PATH}")
    print(f"  Approvals: {approvals}")
    print(f"  Corrections: {corrections}")
    print(f"  Overall agreement rate: {rate:.0%}")


if __name__ == "__main__":
    seed_feedback()
