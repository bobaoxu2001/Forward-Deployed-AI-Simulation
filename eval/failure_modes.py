"""Failure mode taxonomy and detection.

Five failure modes, each with a detector that returns
(detected: bool, detail: str).

Every eval run tags each extraction with its failure modes.
The report shows counts, rates, and examples for each mode.
"""
from dataclasses import dataclass


@dataclass
class FailureTag:
    """One detected failure mode on one case."""
    mode: str           # e.g. "hallucination"
    case_id: str
    detail: str         # human-readable explanation
    extraction: dict    # the extraction that triggered it
    case: dict          # the case that was processed


# --- Failure mode definitions ---

FAILURE_MODES = [
    "hallucination",
    "omission",
    "ambiguity",
    "overconfidence",
    "language_drift",
]


# --- Detectors ---

def detect_hallucination(extraction: dict, case: dict) -> tuple[bool, str]:
    """Recommendation or root cause attribution with no evidence from source text.

    Checks: (1) evidence_quotes is empty, or (2) none of the evidence quotes
    actually appear in the ticket_text or conversation_snippet.
    """
    evidence = extraction.get("evidence_quotes", [])
    if not evidence or all(not q.strip() for q in evidence):
        return True, "No evidence quotes provided"

    # Check if quotes actually appear in the source text
    source_text = (
        case.get("ticket_text", "")
        + " "
        + case.get("conversation_snippet", "")
        + " "
        + " ".join(case.get("email_thread", []))
    ).lower()

    fabricated = []
    for quote in evidence:
        quote_clean = quote.strip().lower()
        if quote_clean and quote_clean not in source_text:
            # Check if at least a substantial substring matches (>= 10 chars)
            found_partial = False
            if len(quote_clean) >= 10:
                for start in range(0, len(quote_clean) - 9):
                    chunk = quote_clean[start : start + 10]
                    if chunk in source_text:
                        found_partial = True
                        break
            if not found_partial:
                fabricated.append(quote)

    if fabricated:
        return True, f"Evidence not found in source: {fabricated[:2]}"

    return False, ""


def detect_omission(extraction: dict, case: dict) -> tuple[bool, str]:
    """Clear signal in the source text that the extraction missed.

    Heuristic: checks for high-signal keywords in source text that should
    have influenced root_cause or risk_level but didn't.
    """
    source_text = (
        case.get("ticket_text", "") + " " + case.get("conversation_snippet", "")
    ).lower()

    risk_level = extraction.get("risk_level", "low")
    root_cause = extraction.get("root_cause_l1", "").lower()

    # Urgent signals that should raise risk_level
    urgent_signals = ["cancel", "lawsuit", "legal action", "report to", "regulator"]
    has_urgent = any(s in source_text for s in urgent_signals)
    if has_urgent and risk_level in ("low", "medium"):
        return True, f"Urgent signals in text but risk_level={risk_level}"

    # Outage/security signals that should affect root_cause
    outage_signals = ["outage", "down for", "service unavailable", "cannot access"]
    has_outage = any(s in source_text for s in outage_signals)
    if has_outage and root_cause not in ("network", "outage", "service", "infrastructure"):
        return True, f"Outage signals in text but root_cause={root_cause}"

    # Billing signals
    billing_signals = ["overcharg", "double charge", "charged twice", "wrong amount", "refund"]
    has_billing = any(s in source_text for s in billing_signals)
    if has_billing and root_cause not in ("billing", "payment", "pricing"):
        return True, f"Billing signals in text but root_cause={root_cause}"

    return False, ""


def detect_ambiguity(extraction: dict, case: dict) -> tuple[bool, str]:
    """Case is genuinely ambiguous but extraction doesn't flag uncertainty.

    Detected when: ticket_text is very short OR contains conflicting signals,
    but confidence is high and review_required is False.
    """
    ticket = case.get("ticket_text", "")
    confidence = extraction.get("confidence", 0)
    review = extraction.get("review_required", False)

    # Very short ticket — hard to be confident
    if len(ticket.split()) < 8 and confidence > 0.8 and not review:
        return True, f"Very short ticket ({len(ticket.split())} words) but confidence={confidence}"

    # Ticket has question marks suggesting ambiguity
    if ticket.count("?") >= 3 and confidence > 0.8 and not review:
        return True, f"Multiple questions in ticket but confidence={confidence}"

    return False, ""


def detect_overconfidence(extraction: dict, case: dict) -> tuple[bool, str]:
    """High confidence but wrong root cause (requires gold label).

    Also triggers if confidence is very high but risk signals are contradictory.
    """
    confidence = extraction.get("confidence", 0)

    # Check against gold label if available
    gold_root_cause = case.get("gold_root_cause")
    if gold_root_cause is None:
        # Fallback: check for high confidence with high churn_risk (contradictory)
        churn_risk = extraction.get("churn_risk", 0)
        risk_level = extraction.get("risk_level", "low")
        if confidence > 0.9 and churn_risk > 0.7 and risk_level in ("high", "critical"):
            return True, f"Confidence={confidence} but churn_risk={churn_risk}, risk={risk_level}"
        return False, ""

    predicted = extraction.get("root_cause_l1", "").lower()
    gold = gold_root_cause.lower()
    if confidence > 0.85 and predicted != gold:
        return True, f"Confidence={confidence} but predicted={predicted}, gold={gold}"

    return False, ""


def detect_language_drift(extraction: dict, case: dict) -> tuple[bool, str]:
    """Multilingual or format shifts cause classification collapse.

    Detected when: case language is non-English or mixed, and the extraction
    has low confidence or ambiguous root cause.
    """
    language = case.get("language", "en")
    confidence = extraction.get("confidence", 0)
    root_cause = extraction.get("root_cause_l1", "").lower()

    if language in ("mixed", "de", "zh", "unknown"):
        if confidence < 0.5:
            return True, f"Non-English case (lang={language}) with low confidence={confidence}"
        if root_cause in ("unknown", "other", "ambiguous", ""):
            return True, f"Non-English case (lang={language}) with ambiguous root_cause={root_cause}"

    return False, ""


# --- Main tagger ---

DETECTORS = {
    "hallucination": detect_hallucination,
    "omission": detect_omission,
    "ambiguity": detect_ambiguity,
    "overconfidence": detect_overconfidence,
    "language_drift": detect_language_drift,
}


def tag_failure_modes(extraction: dict, case: dict) -> list[FailureTag]:
    """Run all failure mode detectors on one extraction.

    Returns a list of FailureTag for each detected failure.
    """
    tags = []
    case_id = case.get("case_id", extraction.get("case_id", "unknown"))

    for mode, detector in DETECTORS.items():
        detected, detail = detector(extraction, case)
        if detected:
            tags.append(FailureTag(
                mode=mode,
                case_id=case_id,
                detail=detail,
                extraction=extraction,
                case=case,
            ))

    return tags


def summarize_failure_modes(all_tags: list[FailureTag]) -> dict:
    """Aggregate failure tags into counts and rates.

    Returns:
        {
            "total_failures": int,
            "by_mode": {"hallucination": {"count": N, "examples": [...]}, ...},
            "affected_cases": int,
        }
    """
    from collections import Counter, defaultdict

    mode_counts = Counter(t.mode for t in all_tags)
    mode_examples: dict[str, list[dict]] = defaultdict(list)

    for t in all_tags:
        if len(mode_examples[t.mode]) < 3:  # Keep up to 3 examples per mode
            mode_examples[t.mode].append({
                "case_id": t.case_id,
                "detail": t.detail,
            })

    by_mode = {}
    for mode in FAILURE_MODES:
        by_mode[mode] = {
            "count": mode_counts.get(mode, 0),
            "examples": mode_examples.get(mode, []),
        }

    affected_cases = len({t.case_id for t in all_tags})

    return {
        "total_failures": len(all_tags),
        "by_mode": by_mode,
        "affected_cases": affected_cases,
    }
