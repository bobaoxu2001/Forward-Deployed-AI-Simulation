"""Tests for risk gating logic."""
from pipeline.gate import compute_gate_decision


def test_low_risk_auto_routes():
    output = {
        "root_cause": {"l1": "billing", "l2": "inquiry", "confidence": 0.9},
        "risk": {"churn_risk": 0.2, "severity": "low", "review_required": False},
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "auto"
    assert decision["reasons"] == []


def test_low_confidence_triggers_review():
    output = {
        "root_cause": {"l1": "billing", "l2": "inquiry", "confidence": 0.4},
        "risk": {"churn_risk": 0.2, "severity": "low", "review_required": False},
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"


def test_high_churn_risk_triggers_review():
    output = {
        "root_cause": {"l1": "billing", "l2": "inquiry", "confidence": 0.9},
        "risk": {"churn_risk": 0.8, "severity": "medium", "review_required": False},
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"


def test_high_risk_category_triggers_review():
    output = {
        "root_cause": {"l1": "security_breach", "l2": "data_leak", "confidence": 0.95},
        "risk": {"churn_risk": 0.3, "severity": "low", "review_required": False},
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"
