"""Text normalization and cleanup for raw inputs."""
import re


def normalize_text(text: str) -> str:
    """Basic text normalization: whitespace, control chars."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_case_bundle(case: dict) -> dict:
    """Normalize all text fields in a case bundle."""
    inputs = case.get("inputs", {})
    if "ticket_text" in inputs:
        inputs["ticket_text"] = normalize_text(inputs["ticket_text"])
    if "conversation_snippet" in inputs:
        inputs["conversation_snippet"] = normalize_text(inputs["conversation_snippet"])
    if "email_thread" in inputs:
        inputs["email_thread"] = [normalize_text(e) for e in inputs["email_thread"]]
    if "resolution_notes" in inputs:
        inputs["resolution_notes"] = normalize_text(inputs["resolution_notes"])
    return case
