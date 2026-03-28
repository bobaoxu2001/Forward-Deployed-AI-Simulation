"""Tests for risk gating logic."""
from pipeline.gate import compute_gate_decision


def test_low_risk_auto_routes():
    output = {
        "root_cause_l1": "billing",
        "root_cause_l2": "inquiry",
        "confidence": 0.9,
        "risk_level": "low",
        "churn_risk": 0.2,
        "review_required": False,
        "evidence_quotes": ["customer asked about bill"],
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "auto"
    assert decision["reasons"] == []


def test_low_confidence_triggers_review():
    output = {
        "root_cause_l1": "billing",
        "confidence": 0.4,
        "risk_level": "low",
        "churn_risk": 0.2,
        "review_required": False,
        "evidence_quotes": ["quote"],
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"
    assert any("confidence" in r.lower() for r in decision["reasons"])


def test_high_churn_risk_triggers_review():
    output = {
        "root_cause_l1": "billing",
        "confidence": 0.9,
        "risk_level": "medium",
        "churn_risk": 0.8,
        "review_required": False,
        "evidence_quotes": ["quote"],
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"


def test_high_risk_category_triggers_review():
    output = {
        "root_cause_l1": "security_breach",
        "confidence": 0.95,
        "risk_level": "low",
        "churn_risk": 0.3,
        "review_required": False,
        "evidence_quotes": ["quote"],
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"
    assert any("category" in r.lower() for r in decision["reasons"])


def test_missing_evidence_triggers_review():
    output = {
        "root_cause_l1": "billing",
        "confidence": 0.9,
        "risk_level": "low",
        "churn_risk": 0.1,
        "review_required": False,
        "evidence_quotes": [],
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"
    assert any("evidence" in r.lower() for r in decision["reasons"])


def test_model_review_flag_triggers_review():
    output = {
        "root_cause_l1": "billing",
        "confidence": 0.9,
        "risk_level": "low",
        "churn_risk": 0.1,
        "review_required": True,
        "evidence_quotes": ["quote"],
    }
    decision = compute_gate_decision(output)
    assert decision["route"] == "review"
