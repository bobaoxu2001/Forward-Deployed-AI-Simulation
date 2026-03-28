"""LLM-based structured extraction from case bundles."""


def extract_structured_output(case: dict, client=None, model: str = "claude-sonnet-4-20250514") -> dict:
    """
    Send case bundle to LLM and get structured output.

    Returns a dict conforming to STRUCTURED_OUTPUT_SCHEMA.
    Placeholder — will be implemented in Phase B.
    """
    raise NotImplementedError("LLM extraction not yet implemented. Phase B.")
