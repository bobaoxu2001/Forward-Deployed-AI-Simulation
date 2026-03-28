"""Text normalization and cleanup for raw inputs."""
import re

from pipeline.schemas import CaseBundle


def normalize_text(text: str) -> str:
    """Clean up a text string: whitespace, control chars, encoding artifacts."""
    if not text:
        return ""
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces/tabs to single space
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines to double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove null bytes and other control chars (keep newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


def normalize_case(case: CaseBundle) -> CaseBundle:
    """Normalize all text fields in a case bundle."""
    case.ticket_text = normalize_text(case.ticket_text)
    case.conversation_snippet = normalize_text(case.conversation_snippet)
    case.email_thread = [normalize_text(e) for e in case.email_thread]

    # Normalize enum fields to lowercase
    case.vip_tier = case.vip_tier.lower().strip() if case.vip_tier else "unknown"
    case.priority = case.priority.lower().strip() if case.priority else "unknown"

    # Clamp handle_time to non-negative
    if case.handle_time_minutes < 0:
        case.handle_time_minutes = 0.0

    return case


def detect_language(text: str) -> str:
    """Simple language detection heuristic.

    Returns 'en' for English-like text, 'mixed' if unsure.
    TODO: Phase A+ — use a proper language detection library if needed.
    """
    if not text:
        return "unknown"
    # Simple heuristic: check for non-ASCII ratio
    non_ascii = sum(1 for c in text if ord(c) > 127)
    ratio = non_ascii / len(text) if text else 0
    if ratio > 0.3:
        return "mixed"
    return "en"
