"""Risk and confidence gating logic."""

HIGH_RISK_CATEGORIES = {"security_breach", "outage", "vip_churn", "data_loss"}
CONFIDENCE_THRESHOLD = 0.7
CHURN_RISK_THRESHOLD = 0.6
HIGH_RISK_SAMPLE_RATE = 0.10


def compute_gate_decision(output: dict) -> dict:
    """
    Decide whether a case should be auto-routed or sent to human review.

    Returns a dict with:
        - route: "auto" | "review"
        - reasons: list of strings explaining the decision
    """
    reasons = []

    root_cause = output.get("root_cause", {})
    risk = output.get("risk", {})

    # Low confidence → review
    if root_cause.get("confidence", 0) < CONFIDENCE_THRESHOLD:
        reasons.append(f"Low confidence: {root_cause.get('confidence')}")

    # High churn risk → review
    if risk.get("churn_risk", 0) >= CHURN_RISK_THRESHOLD:
        reasons.append(f"High churn risk: {risk.get('churn_risk')}")

    # High severity → review
    if risk.get("severity") in ("high", "critical"):
        reasons.append(f"High severity: {risk.get('severity')}")

    # Explicit review flag from model
    if risk.get("review_required"):
        reasons.append("Model flagged review_required=true")

    # High-risk root cause category
    l1 = root_cause.get("l1", "").lower().replace(" ", "_")
    if l1 in HIGH_RISK_CATEGORIES:
        reasons.append(f"High-risk category: {l1}")

    route = "review" if reasons else "auto"
    return {"route": route, "reasons": reasons}
