"""Tests for validate module — covers both case and extraction validation."""
from pipeline.validate import validate_case, validate_extraction, check_evidence_present
from pipeline.schemas import CaseBundle, ExtractionOutput


def test_valid_case_passes():
    d = CaseBundle(case_id="v1", ticket_text="My bill is wrong").to_dict()
    valid, errors = validate_case(d)
    assert valid is True


def test_case_bad_priority_fails():
    d = {"case_id": "v2", "ticket_text": "hi", "priority": "URGENT"}
    valid, errors = validate_case(d)
    assert valid is False


def test_valid_extraction_passes():
    d = ExtractionOutput(
        root_cause_l1="network",
        root_cause_l2="outage",
        sentiment_score=-0.8,
        risk_level="critical",
        review_required=True,
        next_best_actions=["Dispatch technician"],
        evidence_quotes=["internet has been down for 3 days"],
    ).to_dict()
    valid, errors = validate_extraction(d)
    assert valid is True


def test_extraction_out_of_range_sentiment_fails():
    d = ExtractionOutput(
        root_cause_l1="billing",
        sentiment_score=5.0,  # out of range
        risk_level="low",
        next_best_actions=["check"],
        evidence_quotes=["quote"],
    ).to_dict()
    valid, errors = validate_extraction(d)
    assert valid is False


def test_check_evidence_with_content():
    ok, msg = check_evidence_present({"evidence_quotes": ["real quote"]})
    assert ok is True


def test_check_evidence_missing_key():
    ok, msg = check_evidence_present({})
    assert ok is False
