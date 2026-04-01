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
    """Returns diverse, case-aware extractions for demo without API calls.

    When no explicit response is provided, the mock analyzes keyword signals
    in the prompt to produce varied, realistic-looking outputs. This ensures
    the dashboard shows meaningful distributions rather than identical rows.
    """

    # Keyword → (root_cause_l1, root_cause_l2, risk_level, base_confidence) mapping
    _SIGNAL_MAP = [
        (["security", "breach", "sicherheit", "cyberattack", "unauthorized"],
         "security_breach", "unauthorized_access", "critical", 0.80),
        (["outage", "offline", "down", "unavailable", "ausfall"],
         "outage", "service_unavailable", "high", 0.78),
        (["network", "connectivity", "vpn", "router", "wifi", "dns"],
         "network", "connectivity_failure", "medium", 0.82),
        (["billing", "charge", "invoice", "payment", "overcharge", "refund"],
         "billing", "incorrect_charge", "low", 0.88),
        (["account", "login", "password", "signup", "sign-up", "locked"],
         "account", "access_issue", "medium", 0.75),
        (["cancel", "termination", "terminate", "close account"],
         "service", "cancellation_request", "high", 0.72),
        (["upgrade", "feature", "enhancement", "improve", "request"],
         "product", "feature_request", "low", 0.90),
        (["slow", "performance", "latency", "timeout", "lag"],
         "network", "performance_degradation", "medium", 0.80),
        (["data", "loss", "missing", "deleted", "corruption"],
         "data_loss", "data_corruption", "critical", 0.70),
        (["complaint", "dissatisfied", "frustrated", "angry", "worst"],
         "service", "customer_dissatisfaction", "high", 0.76),
    ]

    _FALLBACK = ("service", "general_inquiry", "medium", 0.82)

    def __init__(self, response: dict | None = None):
        self.response = response

    def _classify_prompt(self, prompt: str) -> tuple[str, str, str, float]:
        """Match keywords in the CASE DATA section only (not the prompt template)."""
        import re
        # Extract only the case data block between "CASE DATA:" and "You MUST respond"
        match = re.search(r"CASE DATA:\s*(.*?)(?:You MUST respond)", prompt, re.DOTALL)
        case_text = match.group(1).lower() if match else prompt.lower()
        for keywords, l1, l2, risk, conf in self._SIGNAL_MAP:
            if any(kw in case_text for kw in keywords):
                return l1, l2, risk, conf
        return self._FALLBACK

    def _extract_evidence(self, prompt: str) -> list[str]:
        """Extract short phrases from the prompt as mock evidence quotes."""
        # Find the case text between "Ticket:" and "Metadata:"
        import re
        match = re.search(r"Ticket:\s*(.*?)(?:\nConversation:|\nEmail thread:|\nMetadata:)", prompt, re.DOTALL)
        text = match.group(1).strip() if match else ""
        if not text:
            return ["support case reported by customer"]

        # Split into sentences, take up to 3
        sentences = re.split(r'[.!?\n]+', text)
        quotes = []
        for s in sentences:
            s = s.strip()
            if 15 < len(s) < 200:
                quotes.append(s)
            if len(quotes) >= 3:
                break
        return quotes or [text[:100]]

    def extract(self, prompt: str) -> str:
        if self.response is not None:
            return json.dumps(self.response)

        l1, l2, risk, confidence = self._classify_prompt(prompt)
        evidence = self._extract_evidence(prompt)
        word_count = len(prompt.split())

        # Short-input confidence cap (mirrors v2 prompt rule)
        if word_count < 80:
            confidence = min(confidence, 0.70)

        # Determine review flag and sentiment from risk
        review_required = risk in ("high", "critical") or confidence < 0.7
        sentiment_map = {"critical": -0.8, "high": -0.6, "medium": -0.3, "low": 0.1}
        sentiment = sentiment_map.get(risk, -0.3)
        churn_risk = {"critical": 0.85, "high": 0.65, "medium": 0.35, "low": 0.15}.get(risk, 0.3)

        result = {
            "root_cause_l1": l1,
            "root_cause_l2": l2,
            "sentiment_score": sentiment,
            "risk_level": risk,
            "review_required": review_required,
            "next_best_actions": [
                f"Investigate {l2.replace('_', ' ')} issue",
                f"Escalate to {l1} team for resolution",
            ],
            "evidence_quotes": evidence,
            "confidence": confidence,
            "churn_risk": churn_risk,
            "sentiment_rationale": f"Customer reported {l2.replace('_', ' ')} — {risk} severity",
            "draft_notes": f"Case classified as {l1}/{l2}. Risk: {risk}. "
                           f"{'Requires human review.' if review_required else 'Safe for auto-routing.'}",
        }
        return json.dumps(result)


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
