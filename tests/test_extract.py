"""Tests for extraction pipeline using MockProvider."""
from pipeline.schemas import CaseBundle, ExtractionOutput
from pipeline.extract import (
    extract_case,
    MockProvider,
    build_prompt,
    _try_extract_json,
)


def _sample_case() -> CaseBundle:
    return CaseBundle(
        case_id="test-ext-001",
        ticket_text="I was charged twice for the same service last month.",
        conversation_snippet="Agent: Let me check. Customer: Please hurry.",
        vip_tier="vip",
        priority="high",
    )


def test_extract_with_mock_returns_extraction_output():
    case = _sample_case()
    output, meta = extract_case(case, provider=MockProvider())
    assert isinstance(output, ExtractionOutput)
    assert output.root_cause_l1 == "billing"  # case text mentions "charged"
    assert 0.0 < output.confidence <= 1.0
    assert len(output.evidence_quotes) > 0


def test_extract_metadata_has_required_fields():
    case = _sample_case()
    _, meta = extract_case(case, provider=MockProvider())
    assert "prompt_version" in meta
    assert "latency_ms" in meta
    assert "model_name" in meta
    assert "raw_response" in meta


def test_build_prompt_includes_ticket_text():
    case = _sample_case()
    prompt = build_prompt(case)
    assert "charged twice" in prompt
    assert "vip" in prompt


def test_build_prompt_includes_conversation():
    case = _sample_case()
    prompt = build_prompt(case)
    assert "Please hurry" in prompt


def test_extract_forces_review_when_no_evidence():
    provider = MockProvider(response={
        "root_cause_l1": "billing",
        "root_cause_l2": "unknown",
        "sentiment_score": 0.0,
        "risk_level": "low",
        "review_required": False,
        "next_best_actions": ["check"],
        "evidence_quotes": [],
        "confidence": 0.5,
        "churn_risk": 0.1,
    })
    case = _sample_case()
    output, _ = extract_case(case, provider=provider)
    # Should force review when evidence is missing
    assert output.review_required is True


def test_try_extract_json_from_freeform():
    text = 'Here is the result: {"root_cause_l1": "billing"} done.'
    result = _try_extract_json(text)
    assert result["root_cause_l1"] == "billing"


def test_try_extract_json_fallback_on_garbage():
    result = _try_extract_json("this is not json at all")
    assert result["root_cause_l1"] == "unknown"
    assert result["review_required"] is True
