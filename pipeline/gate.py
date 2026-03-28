"""Risk and confidence gating logic.

Decides whether a case should be auto-routed or sent to human review.
Stores both the decision AND the reason codes (not just True/False).
"""

HIGH_RISK_CATEGORIES = {"security_breach", "outage", "vip_churn", "data_loss"}
CONFIDENCE_THRESHOLD = 0.7
CHURN_RISK_THRESHOLD = 0.6


def compute_gate_decision(output: dict) -> dict:
    """
    Decide whether a case should be auto-routed or sent to human review.

    Rules (any triggers review):
    1. Confidence below threshold
    2. Churn risk above threshold
    3. Risk level is high or critical
    4. Model explicitly flagged review_required
    5. Root cause is a high-risk category
    6. Evidence quotes missing or empty
    7. Root cause is ambiguous/unknown

    Returns:
        {
            "route": "auto" | "review",
            "reasons": ["reason1", "reason2", ...],
            "review_reason_codes": ["low_confidence", "high_churn_risk", ...]
        }
    """
    reasons = []
    reason_codes = []

    confidence = output.get("confidence", 0)
    churn_risk = output.get("churn_risk", 0)
    risk_level = output.get("risk_level", "low")
    review_flag = output.get("review_required", False)
    root_cause_l1 = output.get("root_cause_l1", "").lower().replace(" ", "_")
    evidence = output.get("evidence_quotes", [])

    # Rule 1: Low confidence
    if confidence < CONFIDENCE_THRESHOLD:
        reasons.append(f"Low confidence: {confidence}")
        reason_codes.append("low_confidence")

    # Rule 2: High churn risk
    if churn_risk >= CHURN_RISK_THRESHOLD:
        reasons.append(f"High churn risk: {churn_risk}")
        reason_codes.append("high_churn_risk")

    # Rule 3: High/critical severity
    if risk_level in ("high", "critical"):
        reasons.append(f"High risk level: {risk_level}")
        reason_codes.append("high_risk_level")

    # Rule 4: Model flagged review
    if review_flag:
        reasons.append("Model flagged review_required=true")
        reason_codes.append("model_flagged")

    # Rule 5: High-risk root cause category
    if root_cause_l1 in HIGH_RISK_CATEGORIES:
        reasons.append(f"High-risk category: {root_cause_l1}")
        reason_codes.append("high_risk_category")

    # Rule 6: Missing evidence
    if not evidence or all(not q.strip() for q in evidence if isinstance(q, str)):
        reasons.append("Evidence quotes missing or empty")
        reason_codes.append("missing_evidence")

    # Rule 7: Ambiguous/unknown root cause
    if root_cause_l1 in ("unknown", "ambiguous", "other", ""):
        reasons.append(f"Ambiguous root cause: '{root_cause_l1}'")
        reason_codes.append("ambiguous_root_cause")

    route = "review" if reasons else "auto"
    return {
        "route": route,
        "reasons": reasons,
        "review_reason_codes": reason_codes,
    }
