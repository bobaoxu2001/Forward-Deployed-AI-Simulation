"""Build 20-40 case bundles from raw datasets.

Each case bundle = one customer/incident/problem chain.
Metadata fields (vip_tier, handle_time, churned) are synthetically augmented
where real labels are unavailable. Synthetic logic is explicit and deterministic.
"""
import json
import random
import hashlib
from pathlib import Path

from pipeline.schemas import CaseBundle
from pipeline.normalize import normalize_case, detect_language
from pipeline.loaders import save_case_bundle

RAW_DIR = Path("data/raw")
CASES_DIR = Path("data/cases")

# Deterministic seed for reproducibility
random.seed(42)

# --- Synthetic augmentation rules ---
# These fill in metadata that real datasets don't provide.
# Every synthetic field is documented here.

VIP_TIERS = ["standard", "standard", "standard", "vip", "unknown"]
PRIORITIES = ["low", "medium", "medium", "high", "critical"]


def _synthetic_vip_tier() -> str:
    return random.choice(VIP_TIERS)


def _synthetic_priority() -> str:
    return random.choice(PRIORITIES)


def _synthetic_handle_time() -> float:
    """Random handle time in minutes. VIP-like cases skew higher."""
    return round(random.uniform(3.0, 90.0), 1)


def _synthetic_churn(priority: str, vip_tier: str) -> bool:
    """Churn probability increases with priority and VIP tier.
    This is a simple heuristic, not a model.
    """
    base = 0.1
    if priority in ("high", "critical"):
        base += 0.2
    if vip_tier == "vip":
        base += 0.15
    return random.random() < base


def _make_case_id(source: str, index: int) -> str:
    """Deterministic case ID from source and index."""
    raw = f"{source}:{index}"
    return f"case-{hashlib.md5(raw.encode()).hexdigest()[:8]}"


# --- Build from support tickets ---

def build_from_tickets(max_cases: int = 25) -> list[CaseBundle]:
    """Build case bundles from support ticket JSONL."""
    tickets_path = RAW_DIR / "support_tickets.jsonl"
    if not tickets_path.exists():
        print(f"Warning: {tickets_path} not found. Run scripts/ingest_data.py first.")
        return []

    cases = []
    with open(tickets_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_cases:
                break
            row = json.loads(line)

            # Map ticket fields to case bundle
            ticket_text = row.get("body") or row.get("subject") or ""
            if not ticket_text.strip():
                continue

            priority = (row.get("priority") or "unknown").lower()
            if priority not in ("low", "medium", "high", "critical", "unknown"):
                priority = "unknown"

            vip_tier = _synthetic_vip_tier()
            handle_time = _synthetic_handle_time()

            case = CaseBundle(
                case_id=_make_case_id("ticket", i),
                ticket_text=ticket_text,
                conversation_snippet=row.get("answer", ""),
                email_thread=[],
                vip_tier=vip_tier,
                priority=priority,
                handle_time_minutes=handle_time,
                churned_within_30d=_synthetic_churn(priority, vip_tier),
                source_dataset="support_tickets",
                language=detect_language(ticket_text),
            )
            cases.append(normalize_case(case))

    print(f"Built {len(cases)} cases from support tickets")
    return cases


# --- Build from SAMSum conversations ---

def build_from_samsum(max_cases: int = 15) -> list[CaseBundle]:
    """Build case bundles from SAMSum conversations.

    SAMSum dialogues are repurposed as conversation snippets
    attached to synthetic ticket text.
    """
    samsum_path = RAW_DIR / "samsum_conversations.jsonl"
    if not samsum_path.exists():
        print(f"Warning: {samsum_path} not found. Run scripts/ingest_data.py first.")
        return []

    cases = []
    with open(samsum_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_cases:
                break
            row = json.loads(line)

            dialogue = row.get("dialogue", "")
            summary = row.get("summary", "")
            if not dialogue.strip():
                continue

            # Use the dialogue as conversation_snippet,
            # and the summary as a synthetic ticket text
            vip_tier = _synthetic_vip_tier()
            priority = _synthetic_priority()
            handle_time = _synthetic_handle_time()

            case = CaseBundle(
                case_id=_make_case_id("samsum", i),
                ticket_text=f"Customer conversation summary: {summary}",
                conversation_snippet=dialogue,
                email_thread=[],
                vip_tier=vip_tier,
                priority=priority,
                handle_time_minutes=handle_time,
                churned_within_30d=_synthetic_churn(priority, vip_tier),
                source_dataset="samsum",
                language="en",
            )
            cases.append(normalize_case(case))

    print(f"Built {len(cases)} cases from SAMSum")
    return cases


# --- Main builder ---

def build_all_cases() -> list[CaseBundle]:
    """Build all case bundles and save to data/cases/."""
    CASES_DIR.mkdir(parents=True, exist_ok=True)

    # Clear existing cases
    for old in CASES_DIR.glob("*.json"):
        old.unlink()

    all_cases = []
    all_cases.extend(build_from_tickets(max_cases=25))
    all_cases.extend(build_from_samsum(max_cases=15))

    if not all_cases:
        print("ERROR: No cases built. Ensure raw data exists in data/raw/.")
        print("Run: python scripts/ingest_data.py")
        return []

    for case in all_cases:
        save_case_bundle(case, CASES_DIR)

    print(f"\nTotal: {len(all_cases)} case bundles saved to {CASES_DIR}/")
    return all_cases


if __name__ == "__main__":
    build_all_cases()
