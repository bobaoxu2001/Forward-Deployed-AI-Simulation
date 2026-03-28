"""Schemas for case bundles and extraction outputs.

These are the source of truth for the entire pipeline.
If you change a schema here, update all downstream code.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional


# --- Case Bundle Schema ---
# Flat structure: one case = one customer/incident/problem chain

@dataclass
class CaseBundle:
    """Input case bundle representing one support incident."""
    case_id: str
    ticket_text: str
    email_thread: list[str] = field(default_factory=list)
    conversation_snippet: str = ""
    vip_tier: str = "unknown"          # "standard" | "vip" | "unknown"
    priority: str = "unknown"          # "low" | "medium" | "high" | "critical" | "unknown"
    handle_time_minutes: float = 0.0
    churned_within_30d: bool = False
    source_dataset: str = ""
    language: str = "en"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CaseBundle":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known_fields}
        return cls(**filtered)


# --- Extraction Output Schema ---
# What the LLM produces for each case

@dataclass
class ExtractionOutput:
    """Structured output from LLM extraction."""
    root_cause_l1: str = ""
    root_cause_l2: str = ""
    sentiment_score: float = 0.0       # -1.0 to 1.0
    risk_level: str = "low"            # "low" | "medium" | "high" | "critical"
    review_required: bool = False
    next_best_actions: list[str] = field(default_factory=list)
    evidence_quotes: list[str] = field(default_factory=list)
    confidence: float = 0.0           # 0.0 to 1.0
    churn_risk: float = 0.0           # 0.0 to 1.0
    sentiment_rationale: str = ""
    draft_notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ExtractionOutput":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known_fields}
        return cls(**filtered)


# --- JSON Schema for validation ---
# Used by jsonschema to validate serialized dicts

CASE_SCHEMA = {
    "type": "object",
    "required": ["case_id", "ticket_text"],
    "properties": {
        "case_id": {"type": "string", "minLength": 1},
        "ticket_text": {"type": "string", "minLength": 1},
        "email_thread": {"type": "array", "items": {"type": "string"}},
        "conversation_snippet": {"type": "string"},
        "vip_tier": {"type": "string", "enum": ["standard", "vip", "unknown"]},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "critical", "unknown"]},
        "handle_time_minutes": {"type": "number", "minimum": 0},
        "churned_within_30d": {"type": "boolean"},
        "source_dataset": {"type": "string"},
        "language": {"type": "string"},
    },
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "required": [
        "root_cause_l1",
        "root_cause_l2",
        "sentiment_score",
        "risk_level",
        "review_required",
        "next_best_actions",
        "evidence_quotes",
    ],
    "properties": {
        "root_cause_l1": {"type": "string", "minLength": 1},
        "root_cause_l2": {"type": "string"},
        "sentiment_score": {"type": "number", "minimum": -1, "maximum": 1},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "review_required": {"type": "boolean"},
        "next_best_actions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "evidence_quotes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "churn_risk": {"type": "number", "minimum": 0, "maximum": 1},
        "sentiment_rationale": {"type": "string"},
        "draft_notes": {"type": "string"},
    },
}
