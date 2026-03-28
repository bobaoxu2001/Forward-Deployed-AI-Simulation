"""Validation for case bundles and extraction outputs."""
import jsonschema

from pipeline.schemas import CASE_SCHEMA, EXTRACTION_SCHEMA


def validate_case(data: dict) -> tuple[bool, list[str]]:
    """Validate a case dict against CASE_SCHEMA.

    Returns (is_valid, list_of_error_messages).
    """
    validator = jsonschema.Draft202012Validator(CASE_SCHEMA)
    errors = [e.message for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def validate_extraction(data: dict) -> tuple[bool, list[str]]:
    """Validate an extraction output dict against EXTRACTION_SCHEMA.

    Returns (is_valid, list_of_error_messages).
    """
    validator = jsonschema.Draft202012Validator(EXTRACTION_SCHEMA)
    errors = [e.message for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def check_evidence_present(extraction: dict) -> tuple[bool, str]:
    """Check that evidence_quotes is non-empty.

    Every extraction must have at least one evidence quote.
    Returns (has_evidence, message).
    """
    quotes = extraction.get("evidence_quotes", [])
    if not quotes:
        return False, "No evidence quotes provided"
    if all(not q.strip() for q in quotes):
        return False, "All evidence quotes are empty strings"
    return True, "OK"
