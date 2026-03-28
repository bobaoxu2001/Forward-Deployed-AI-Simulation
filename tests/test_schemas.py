"""Tests for schemas, loaders, normalize, and validation."""
import json
import tempfile
from pathlib import Path

from pipeline.schemas import CaseBundle, ExtractionOutput
from pipeline.loaders import save_case_bundle, load_case_bundle, load_all_cases
from pipeline.normalize import normalize_text, normalize_case, detect_language
from pipeline.validate import validate_case, validate_extraction, check_evidence_present


# --- CaseBundle dataclass ---

def test_case_bundle_roundtrip():
    case = CaseBundle(
        case_id="test-001",
        ticket_text="My internet is down since yesterday.",
        vip_tier="vip",
        priority="high",
        handle_time_minutes=15.5,
        churned_within_30d=True,
    )
    d = case.to_dict()
    restored = CaseBundle.from_dict(d)
    assert restored.case_id == "test-001"
    assert restored.ticket_text == "My internet is down since yesterday."
    assert restored.vip_tier == "vip"
    assert restored.churned_within_30d is True


def test_case_bundle_from_dict_ignores_extra_fields():
    d = {"case_id": "x", "ticket_text": "hello", "unknown_field": 999}
    case = CaseBundle.from_dict(d)
    assert case.case_id == "x"
    assert not hasattr(case, "unknown_field")


def test_case_bundle_defaults():
    case = CaseBundle(case_id="x", ticket_text="hi")
    assert case.vip_tier == "unknown"
    assert case.priority == "unknown"
    assert case.email_thread == []
    assert case.churned_within_30d is False


# --- ExtractionOutput dataclass ---

def test_extraction_output_roundtrip():
    ext = ExtractionOutput(
        root_cause_l1="billing",
        root_cause_l2="overcharge",
        sentiment_score=-0.7,
        risk_level="high",
        review_required=True,
        next_best_actions=["Issue refund"],
        evidence_quotes=["charged twice for same service"],
    )
    d = ext.to_dict()
    restored = ExtractionOutput.from_dict(d)
    assert restored.root_cause_l1 == "billing"
    assert restored.review_required is True


# --- Normalize ---

def test_normalize_text_whitespace():
    assert normalize_text("  hello   world  ") == "hello world"


def test_normalize_text_newlines():
    assert normalize_text("a\n\n\n\nb") == "a\n\nb"


def test_normalize_text_empty():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""  # type: ignore


def test_normalize_case_clamps_handle_time():
    case = CaseBundle(case_id="x", ticket_text="test", handle_time_minutes=-5.0)
    normalized = normalize_case(case)
    assert normalized.handle_time_minutes == 0.0


def test_detect_language_english():
    assert detect_language("Hello, my internet is broken") == "en"


def test_detect_language_mixed():
    assert detect_language("这是中文文本加some English") == "mixed"


# --- Validate ---

def test_validate_case_valid():
    d = CaseBundle(case_id="x", ticket_text="hello").to_dict()
    valid, errors = validate_case(d)
    assert valid is True
    assert errors == []


def test_validate_case_missing_ticket_text():
    d = {"case_id": "x"}
    valid, errors = validate_case(d)
    assert valid is False
    assert any("ticket_text" in e for e in errors)


def test_validate_case_empty_case_id():
    d = {"case_id": "", "ticket_text": "hi"}
    valid, errors = validate_case(d)
    assert valid is False


def test_validate_extraction_valid():
    d = ExtractionOutput(
        root_cause_l1="billing",
        root_cause_l2="overcharge",
        sentiment_score=-0.5,
        risk_level="high",
        review_required=True,
        next_best_actions=["Refund"],
        evidence_quotes=["charged twice"],
    ).to_dict()
    valid, errors = validate_extraction(d)
    assert valid is True


def test_validate_extraction_empty_actions():
    d = ExtractionOutput(
        root_cause_l1="billing",
        sentiment_score=0.0,
        risk_level="low",
        next_best_actions=[],
        evidence_quotes=["some quote"],
    ).to_dict()
    valid, errors = validate_extraction(d)
    assert valid is False  # minItems: 1


def test_validate_extraction_no_evidence():
    d = ExtractionOutput(
        root_cause_l1="billing",
        sentiment_score=0.0,
        risk_level="low",
        next_best_actions=["Do something"],
        evidence_quotes=[],
    ).to_dict()
    valid, errors = validate_extraction(d)
    assert valid is False  # minItems: 1


def test_check_evidence_present_ok():
    d = {"evidence_quotes": ["customer said X"]}
    ok, msg = check_evidence_present(d)
    assert ok is True


def test_check_evidence_present_empty():
    d = {"evidence_quotes": []}
    ok, msg = check_evidence_present(d)
    assert ok is False


def test_check_evidence_present_blank_strings():
    d = {"evidence_quotes": ["", "  "]}
    ok, msg = check_evidence_present(d)
    assert ok is False


# --- Loaders: save/load round trip ---

def test_save_and_load_case_bundle():
    case = CaseBundle(
        case_id="roundtrip-001",
        ticket_text="Test ticket for round trip.",
        vip_tier="standard",
        priority="low",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        save_case_bundle(case, tmpdir)
        loaded = load_case_bundle(Path(tmpdir) / "roundtrip-001.json")
        assert loaded.case_id == "roundtrip-001"
        assert loaded.ticket_text == "Test ticket for round trip."


def test_load_all_cases():
    c1 = CaseBundle(case_id="a", ticket_text="first")
    c2 = CaseBundle(case_id="b", ticket_text="second")
    with tempfile.TemporaryDirectory() as tmpdir:
        save_case_bundle(c1, tmpdir)
        save_case_bundle(c2, tmpdir)
        cases = load_all_cases(tmpdir)
        assert len(cases) == 2
        ids = {c.case_id for c in cases}
        assert ids == {"a", "b"}
