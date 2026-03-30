"""LLM-based structured extraction from case bundles.

The model-calling code is isolated in one function (call_llm).
To switch providers, replace call_llm — everything else stays the same.
"""
import json
import os
import time
from typing import Protocol

from pipeline.schemas import CaseBundle, ExtractionOutput


# --- Provider interface ---

class LLMProvider(Protocol):
    """Interface for LLM providers. Implement this to swap models."""

    def extract(self, prompt: str) -> str:
        """Send prompt, return raw text response."""
        ...


# --- Claude provider ---

class ClaudeProvider:
    """Extraction via Anthropic Claude API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def extract(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


# --- Mock provider for testing ---

class MockProvider:
    """Returns a fixed extraction for testing without API calls."""

    def __init__(self, response: dict | None = None):
        self.response = response or {
            "root_cause_l1": "billing",
            "root_cause_l2": "overcharge",
            "sentiment_score": -0.5,
            "risk_level": "medium",
            "review_required": False,
            "next_best_actions": ["Issue credit", "Follow up in 48h"],
            "evidence_quotes": ["I was charged twice for the same service"],
            "confidence": 0.85,
            "churn_risk": 0.3,
            "sentiment_rationale": "Customer frustrated about billing error",
            "draft_notes": "Customer reports duplicate charge. Verify and issue credit.",
        }

    def extract(self, prompt: str) -> str:
        return json.dumps(self.response)


# --- Prompt construction ---

EXTRACTION_PROMPT_TEMPLATE = """You are an enterprise support analyst. Analyze the following support case and extract structured information.

CASE DATA:
{case_text}

You MUST respond with a valid JSON object matching this exact schema:
{{
  "root_cause_l1": "<top-level category: billing, network, account, product, service, security_breach, outage, other>",
  "root_cause_l2": "<specific sub-category>",
  "sentiment_score": <float from -1.0 (very negative) to 1.0 (very positive)>,
  "risk_level": "<low | medium | high | critical>",
  "review_required": <true if uncertain or high-risk, false otherwise>,
  "next_best_actions": ["<action 1>", "<action 2>"],
  "evidence_quotes": ["<exact quote from the case text supporting your analysis>", ...],
  "confidence": <float from 0.0 to 1.0>,
  "churn_risk": <float from 0.0 to 1.0>,
  "sentiment_rationale": "<one sentence explaining sentiment>",
  "draft_notes": "<draft resolution notes for the agent>"
}}

RULES:
- evidence_quotes MUST contain exact phrases from the case text, not your own words
- If you cannot find evidence for a field, set review_required to true
- If the case text is ambiguous, set confidence below 0.7
- If the case text is very short (under ~30 words), cap confidence at 0.7 — brief inputs lack context for high-certainty analysis
- Do NOT hallucinate evidence — only quote text that actually appears above
- Respond ONLY with the JSON object, no other text"""

PROMPT_VERSION = "v2"


def build_prompt(case: CaseBundle) -> str:
    """Build the extraction prompt from a case bundle."""
    parts = [f"Ticket: {case.ticket_text}"]

    if case.conversation_snippet:
        parts.append(f"\nConversation: {case.conversation_snippet}")

    if case.email_thread:
        thread = "\n---\n".join(case.email_thread)
        parts.append(f"\nEmail thread:\n{thread}")

    parts.append(f"\nMetadata: priority={case.priority}, vip={case.vip_tier}")

    case_text = "\n".join(parts)
    return EXTRACTION_PROMPT_TEMPLATE.format(case_text=case_text)


# --- Main extraction function ---

def extract_case(
    case: CaseBundle,
    provider: LLMProvider | None = None,
) -> tuple[ExtractionOutput, dict]:
    """
    Extract structured output from a case bundle.

    Args:
        case: Normalized case bundle
        provider: LLM provider (defaults to ClaudeProvider)

    Returns:
        (extraction_output, metadata_dict)
        metadata_dict contains: prompt_version, model_name, latency_ms, raw_response
    """
    if provider is None:
        provider = ClaudeProvider()

    prompt = build_prompt(case)

    start = time.time()
    raw_response = provider.extract(prompt)
    latency_ms = (time.time() - start) * 1000

    # Parse JSON from response
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        # Try to extract JSON from freeform response
        data = _try_extract_json(raw_response)

    # If evidence is missing, force review
    if not data.get("evidence_quotes"):
        data["review_required"] = True
        data["evidence_quotes"] = []

    output = ExtractionOutput.from_dict(data)

    metadata = {
        "prompt_version": PROMPT_VERSION,
        "model_name": getattr(provider, "model", "unknown"),
        "latency_ms": round(latency_ms, 1),
        "raw_response": raw_response,
    }

    return output, metadata


def _try_extract_json(text: str) -> dict:
    """Try to find and parse a JSON object in freeform text."""
    # Look for { ... } pattern
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # If we can't parse, return a minimal valid structure that forces review
    return {
        "root_cause_l1": "unknown",
        "root_cause_l2": "parse_failure",
        "sentiment_score": 0.0,
        "risk_level": "high",
        "review_required": True,
        "next_best_actions": ["Manual review required - extraction failed"],
        "evidence_quotes": [],
        "confidence": 0.0,
        "churn_risk": 0.0,
        "sentiment_rationale": "Could not parse LLM response",
        "draft_notes": "Extraction failed. Raw response needs manual review.",
    }
