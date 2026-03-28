"""JSON schemas for case bundles and structured outputs."""

CASE_BUNDLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "case_bundle",
    "type": "object",
    "required": ["case_id", "inputs", "metadata", "labels"],
    "properties": {
        "case_id": {"type": "string"},
        "inputs": {
            "type": "object",
            "required": ["ticket_text"],
            "properties": {
                "ticket_text": {"type": "string"},
                "conversation_snippet": {"type": "string"},
                "email_thread": {"type": "array", "items": {"type": "string"}},
                "resolution_notes": {"type": "string"},
            },
        },
        "metadata": {
            "type": "object",
            "properties": {
                "source_dataset": {"type": "string"},
                "language": {
                    "type": "string",
                    "enum": ["en", "de", "zh", "mixed"],
                },
                "vip_tier": {
                    "type": "string",
                    "enum": ["standard", "vip", "unknown"],
                },
                "queue": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical", "unknown"],
                },
                "handle_time_minutes": {"type": "number"},
            },
        },
        "labels": {
            "type": "object",
            "properties": {
                "churned_within_30d": {"type": "boolean"},
                "gold_root_cause": {"type": "string"},
                "review_required_gold": {"type": "boolean"},
            },
        },
    },
}

STRUCTURED_OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ticket_structured_output",
    "type": "object",
    "required": ["root_cause", "sentiment", "risk", "recommendation", "evidence"],
    "properties": {
        "root_cause": {
            "type": "object",
            "required": ["l1", "l2", "confidence"],
            "properties": {
                "l1": {"type": "string"},
                "l2": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "sentiment": {
            "type": "object",
            "required": ["score", "rationale"],
            "properties": {
                "score": {"type": "number", "minimum": -1, "maximum": 1},
                "rationale": {"type": "string"},
            },
        },
        "risk": {
            "type": "object",
            "required": ["churn_risk", "severity", "review_required"],
            "properties": {
                "churn_risk": {"type": "number", "minimum": 0, "maximum": 1},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "review_required": {"type": "boolean"},
            },
        },
        "recommendation": {
            "type": "object",
            "required": ["next_best_actions", "draft_notes"],
            "properties": {
                "next_best_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "draft_notes": {"type": "string"},
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["field", "quote"],
                "properties": {
                    "field": {"type": "string"},
                    "quote": {"type": "string"},
                },
            },
        },
    },
}
