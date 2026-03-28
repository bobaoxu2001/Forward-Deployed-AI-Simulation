"""Post-validation for structured outputs against JSON schemas."""
import jsonschema

from pipeline.schemas import STRUCTURED_OUTPUT_SCHEMA


def validate_output(output: dict) -> tuple[bool, list[str]]:
    """
    Validate structured output against schema.

    Returns (is_valid, list_of_errors).
    """
    validator = jsonschema.Draft202012Validator(STRUCTURED_OUTPUT_SCHEMA)
    errors = [e.message for e in validator.iter_errors(output)]
    return len(errors) == 0, errors


def check_evidence_coverage(output: dict) -> tuple[bool, list[str]]:
    """
    Check that key output fields have supporting evidence quotes.

    Returns (all_covered, list_of_unsupported_fields).
    """
    required_fields = {"root_cause", "sentiment", "risk", "recommendation"}
    evidence_fields = {e["field"] for e in output.get("evidence", [])}
    missing = required_fields - evidence_fields
    return len(missing) == 0, list(missing)
