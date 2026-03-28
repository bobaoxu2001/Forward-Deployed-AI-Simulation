"""Tests for evaluation metrics, failure modes, and report generation."""
from eval.metrics import (
    schema_pass_rate,
    evidence_coverage_rate,
    review_required_rate,
    unsupported_recommendation_rate,
    root_cause_consistency,
    review_routing_precision_recall,
    compute_all_metrics,
)
from eval.failure_modes import (
    detect_hallucination,
    detect_omission,
    detect_ambiguity,
    detect_overconfidence,
    detect_language_drift,
    tag_failure_modes,
    summarize_failure_modes,
)
from eval.run_eval import generate_report


# --- Helpers ---

def _valid_extraction(**overrides) -> dict:
    base = {
        "case_id": "test-001",
        "root_cause_l1": "billing",
        "root_cause_l2": "overcharge",
        "sentiment_score": -0.5,
        "risk_level": "medium",
        "review_required": False,
        "next_best_actions": ["Issue refund"],
        "evidence_quotes": ["I was charged twice"],
        "confidence": 0.85,
        "churn_risk": 0.3,
        "sentiment_rationale": "Frustrated",
        "draft_notes": "Check billing.",
    }
    base.update(overrides)
    return base


def _valid_case(**overrides) -> dict:
    base = {
        "case_id": "test-001",
        "ticket_text": "I was charged twice for the same service last month.",
        "conversation_snippet": "",
        "email_thread": [],
        "vip_tier": "standard",
        "priority": "medium",
        "source_dataset": "tickets",
        "language": "en",
    }
    base.update(overrides)
    return base


# --- Metrics tests ---

def test_schema_pass_rate_all_pass():
    exts = [_valid_extraction() for _ in range(5)]
    assert schema_pass_rate(exts) == 1.0


def test_schema_pass_rate_some_fail():
    exts = [_valid_extraction(), {"root_cause_l1": ""}]  # second fails minLength
    rate = schema_pass_rate(exts)
    assert rate == 0.5


def test_schema_pass_rate_empty():
    assert schema_pass_rate([]) == 0.0


def test_evidence_coverage_all_covered():
    exts = [_valid_extraction() for _ in range(3)]
    assert evidence_coverage_rate(exts) == 1.0


def test_evidence_coverage_some_missing():
    exts = [_valid_extraction(), _valid_extraction(evidence_quotes=[])]
    assert evidence_coverage_rate(exts) == 0.5


def test_review_required_rate():
    exts = [
        _valid_extraction(confidence=0.9, risk_level="low", churn_risk=0.1),
        _valid_extraction(confidence=0.3, risk_level="high", churn_risk=0.8),
    ]
    rate = review_required_rate(exts)
    assert rate == 0.5  # second triggers review


def test_unsupported_recommendation_rate():
    exts = [
        _valid_extraction(),  # has evidence
        _valid_extraction(evidence_quotes=[], next_best_actions=["Do X"]),  # unsupported
    ]
    rate = unsupported_recommendation_rate(exts)
    assert rate == 0.5


def test_root_cause_consistency_perfect():
    exts = [
        _valid_extraction(case_id="a", root_cause_l1="billing"),
        _valid_extraction(case_id="b", root_cause_l1="billing"),
    ]
    cases = [
        _valid_case(case_id="a", source_dataset="tickets"),
        _valid_case(case_id="b", source_dataset="tickets"),
    ]
    assert root_cause_consistency(exts, cases) == 1.0


def test_root_cause_consistency_mixed():
    exts = [
        _valid_extraction(case_id="a", root_cause_l1="billing"),
        _valid_extraction(case_id="b", root_cause_l1="network"),
    ]
    cases = [
        _valid_case(case_id="a", source_dataset="tickets"),
        _valid_case(case_id="b", source_dataset="tickets"),
    ]
    assert root_cause_consistency(exts, cases) == 0.5


def test_review_routing_precision_recall():
    pred = [True, True, False, False]
    gold = [True, False, False, True]
    result = review_routing_precision_recall(pred, gold)
    assert result["precision"] == 0.5  # 1 TP / (1 TP + 1 FP)
    assert result["recall"] == 0.5     # 1 TP / (1 TP + 1 FN)


def test_compute_all_metrics_returns_all_keys():
    exts = [_valid_extraction()]
    result = compute_all_metrics(exts)
    assert "schema_pass_rate" in result
    assert "evidence_coverage_rate" in result
    assert "review_required_rate" in result
    assert "unsupported_recommendation_rate" in result
    assert "root_cause_consistency" in result


# --- Failure mode tests ---

def test_detect_hallucination_no_evidence():
    ext = _valid_extraction(evidence_quotes=[])
    case = _valid_case()
    detected, detail = detect_hallucination(ext, case)
    assert detected is True


def test_detect_hallucination_fabricated_quote():
    ext = _valid_extraction(evidence_quotes=["This quote does not exist in the text at all whatsoever"])
    case = _valid_case(ticket_text="My bill is wrong.")
    detected, detail = detect_hallucination(ext, case)
    assert detected is True


def test_detect_hallucination_valid_quote():
    ext = _valid_extraction(evidence_quotes=["charged twice"])
    case = _valid_case(ticket_text="I was charged twice for the same service.")
    detected, detail = detect_hallucination(ext, case)
    assert detected is False


def test_detect_omission_urgent_signal():
    ext = _valid_extraction(risk_level="low")
    case = _valid_case(ticket_text="I will take legal action if this is not resolved.")
    detected, detail = detect_omission(ext, case)
    assert detected is True


def test_detect_omission_no_signal():
    ext = _valid_extraction(risk_level="medium", root_cause_l1="billing")
    case = _valid_case(ticket_text="I was charged twice for the same service.")
    detected, detail = detect_omission(ext, case)
    assert detected is False


def test_detect_ambiguity_short_ticket():
    ext = _valid_extraction(confidence=0.95, review_required=False)
    case = _valid_case(ticket_text="Help please")
    detected, detail = detect_ambiguity(ext, case)
    assert detected is True


def test_detect_ambiguity_normal_ticket():
    ext = _valid_extraction(confidence=0.85, review_required=False)
    case = _valid_case(ticket_text="I was charged twice for the same service and want a refund.")
    detected, detail = detect_ambiguity(ext, case)
    assert detected is False


def test_detect_overconfidence_wrong_label():
    ext = _valid_extraction(confidence=0.95, root_cause_l1="network")
    case = _valid_case(gold_root_cause="billing")
    detected, detail = detect_overconfidence(ext, case)
    assert detected is True


def test_detect_overconfidence_correct_label():
    ext = _valid_extraction(confidence=0.95, root_cause_l1="billing")
    case = _valid_case(gold_root_cause="billing")
    detected, detail = detect_overconfidence(ext, case)
    assert detected is False


def test_detect_language_drift():
    ext = _valid_extraction(confidence=0.3)
    case = _valid_case(language="mixed")
    detected, detail = detect_language_drift(ext, case)
    assert detected is True


def test_detect_language_drift_english():
    ext = _valid_extraction(confidence=0.9)
    case = _valid_case(language="en")
    detected, detail = detect_language_drift(ext, case)
    assert detected is False


def test_tag_failure_modes_returns_list():
    ext = _valid_extraction(evidence_quotes=[])
    case = _valid_case()
    tags = tag_failure_modes(ext, case)
    assert isinstance(tags, list)
    assert any(t.mode == "hallucination" for t in tags)


def test_summarize_failure_modes():
    ext = _valid_extraction(evidence_quotes=[])
    case = _valid_case()
    tags = tag_failure_modes(ext, case)
    summary = summarize_failure_modes(tags)
    assert "total_failures" in summary
    assert "by_mode" in summary
    assert "affected_cases" in summary


# --- Report tests ---

def test_generate_report_not_empty():
    results = {
        "total_cases": 10,
        "metrics": compute_all_metrics([_valid_extraction()]),
        "failure_modes": {"total_failures": 0, "by_mode": {}, "affected_cases": 0},
        "gate_distribution": {"auto": 8, "review": 2},
        "review_reason_codes": {"low_confidence": 2},
    }
    report = generate_report(results)
    assert "# Evaluation Report" in report
    assert "schema_pass_rate" in report
    assert "PASS" in report or "FAIL" in report


def test_generate_report_empty_results():
    report = generate_report({})
    assert "No results" in report
