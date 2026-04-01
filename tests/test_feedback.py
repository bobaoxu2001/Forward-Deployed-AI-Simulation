"""Tests for the human feedback loop module."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from pipeline.feedback import (
    save_feedback,
    save_approval,
    load_all_feedback,
    compute_agreement_stats,
    _reviewable_fields,
    _compute_field_agreement,
    FEEDBACK_PATH,
)


def _with_tmp_feedback(func):
    """Decorator to redirect feedback writes to a temp file."""
    def wrapper(*args, **kwargs):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            tmp_path = Path(f.name)
        with patch("pipeline.feedback.FEEDBACK_PATH", tmp_path):
            try:
                return func(tmp_path, *args, **kwargs)
            finally:
                tmp_path.unlink(missing_ok=True)
    return wrapper


@_with_tmp_feedback
def test_save_approval_creates_entry(tmp_path):
    entry = save_approval("case-001", {"root_cause_l1": "billing"}, "Looks good")
    assert entry["action"] == "approval"
    assert entry["case_id"] == "case-001"
    assert entry["agreement"]["agreement_rate"] == 1.0
    assert entry["reviewer_notes"] == "Looks good"


@_with_tmp_feedback
def test_save_feedback_records_correction(tmp_path):
    original = {"root_cause_l1": "billing", "risk_level": "low", "confidence": 0.9}
    corrected = {"root_cause_l1": "network", "risk_level": "high"}
    entry = save_feedback("case-002", original, corrected, "Wrong root cause")

    assert entry["action"] == "correction"
    assert entry["original"] == {"root_cause_l1": "billing", "risk_level": "low"}
    assert entry["corrected"] == corrected
    assert "root_cause_l1" in entry["agreement"]["fields_corrected"]
    assert "risk_level" in entry["agreement"]["fields_corrected"]
    assert entry["agreement"]["agreement_rate"] < 1.0


@_with_tmp_feedback
def test_load_all_feedback_roundtrip(tmp_path):
    save_approval("case-001", {})
    save_feedback("case-002", {"root_cause_l1": "billing"}, {"root_cause_l1": "network"})

    entries = load_all_feedback()
    assert len(entries) == 2
    assert entries[0]["action"] == "approval"
    assert entries[1]["action"] == "correction"


@_with_tmp_feedback
def test_load_empty_feedback(tmp_path):
    entries = load_all_feedback()
    assert entries == []


@_with_tmp_feedback
def test_compute_agreement_stats_empty(tmp_path):
    stats = compute_agreement_stats()
    assert stats["total_reviews"] == 0
    assert stats["overall_agreement_rate"] == 0.0


@_with_tmp_feedback
def test_compute_agreement_stats_all_approvals(tmp_path):
    save_approval("case-001", {})
    save_approval("case-002", {})

    stats = compute_agreement_stats()
    assert stats["total_reviews"] == 2
    assert stats["approvals"] == 2
    assert stats["corrections"] == 0
    assert stats["overall_agreement_rate"] == 1.0


@_with_tmp_feedback
def test_compute_agreement_stats_mixed(tmp_path):
    save_approval("case-001", {})
    save_feedback("case-002", {"root_cause_l1": "billing"}, {"root_cause_l1": "network"})

    stats = compute_agreement_stats()
    assert stats["total_reviews"] == 2
    assert stats["approvals"] == 1
    assert stats["corrections"] == 1
    assert 0.0 < stats["overall_agreement_rate"] < 1.0
    # root_cause_l1 was corrected in one of two reviews
    assert stats["per_field_agreement"]["root_cause_l1"] == 0.5
    assert stats["most_corrected_fields"][0] == ("root_cause_l1", 1)


@_with_tmp_feedback
def test_compute_agreement_per_field(tmp_path):
    # Correct 2 different fields across 2 reviews
    save_feedback("case-001", {"root_cause_l1": "billing"}, {"root_cause_l1": "network"})
    save_feedback("case-002", {"risk_level": "low"}, {"risk_level": "high"})

    stats = compute_agreement_stats()
    # root_cause_l1 was corrected once out of 2 reviews
    assert stats["per_field_agreement"]["root_cause_l1"] == 0.5
    # risk_level was corrected once out of 2 reviews
    assert stats["per_field_agreement"]["risk_level"] == 0.5
    # confidence was never corrected
    assert stats["per_field_agreement"]["confidence"] == 1.0


def test_reviewable_fields_match_schema():
    """Ensure all reviewable fields exist in ExtractionOutput."""
    from pipeline.schemas import ExtractionOutput
    schema_fields = {f.name for f in ExtractionOutput.__dataclass_fields__.values()}
    for field in _reviewable_fields():
        assert field in schema_fields, f"Reviewable field '{field}' not in ExtractionOutput"


def test_compute_field_agreement_no_corrections():
    agreement = _compute_field_agreement(
        {"root_cause_l1": "billing", "risk_level": "low"},
        {},
    )
    assert agreement["agreement_rate"] == 1.0
    assert agreement["fields_corrected"] == []


def test_compute_field_agreement_all_corrected():
    corrected = {field: "new_value" for field in _reviewable_fields()}
    agreement = _compute_field_agreement({}, corrected)
    assert agreement["agreement_rate"] == 0.0
    assert len(agreement["fields_corrected"]) == len(_reviewable_fields())
