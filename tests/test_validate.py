"""Tests for output validation."""
from pipeline.validate import validate_output, check_evidence_coverage


def _make_valid_output():
    return {
        "root_cause": {"l1": "billing", "l2": "overcharge", "confidence": 0.85},
        "sentiment": {"score": -0.6, "rationale": "Customer is frustrated about charges"},
        "risk": {"churn_risk": 0.7, "severity": "high", "review_required": True},
        "recommendation": {
            "next_best_actions": ["Issue refund", "Escalate to billing team"],
            "draft_notes": "Customer overcharged on last invoice.",
        },
        "evidence": [
            {"field": "root_cause", "quote": "I was charged twice for the same service"},
            {"field": "sentiment", "quote": "This is absolutely unacceptable"},
            {"field": "risk", "quote": "I will switch providers if this isn't resolved"},
            {"field": "recommendation", "quote": "charged twice"},
        ],
    }


def test_valid_output_passes():
    output = _make_valid_output()
    valid, errors = validate_output(output)
    assert valid is True
    assert errors == []


def test_missing_field_fails():
    output = _make_valid_output()
    del output["root_cause"]
    valid, errors = validate_output(output)
    assert valid is False


def test_evidence_coverage_complete():
    output = _make_valid_output()
    covered, missing = check_evidence_coverage(output)
    assert covered is True
    assert missing == []


def test_evidence_coverage_missing():
    output = _make_valid_output()
    output["evidence"] = [{"field": "root_cause", "quote": "test"}]
    covered, missing = check_evidence_coverage(output)
    assert covered is False
    assert len(missing) > 0
