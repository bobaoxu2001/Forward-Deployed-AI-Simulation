"""Build 20-40 case bundles from raw datasets.

Each case bundle = one customer/incident/problem chain.

Field provenance (real vs synthetic):
  REAL from Tobi-Bueck/customer-support-tickets:
    - ticket_text (from body)
    - email_thread (from answer)
    - priority (from priority field)
    - language (from language field)
    - source_dataset tags: tag_1..tag_8, queue, type

  REAL from Bitext dataset:
    - conversation_snippet (from instruction + response)
    - ticket_text (constructed from category + instruction)

  SYNTHETIC (always):
    - vip_tier — no real VIP labels available
    - handle_time_minutes — no real handle times available
    - churned_within_30d — no real churn labels available

Synthetic logic is deterministic (seed=42) and explicitly documented.
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


# ---------------------------------------------------------------------------
# Synthetic augmentation (only for fields that have no real source)
# ---------------------------------------------------------------------------

VIP_TIERS = ["standard", "standard", "standard", "vip", "unknown"]
PRIORITIES = ["low", "medium", "medium", "high", "critical"]


def _synthetic_vip_tier() -> str:
    """SYNTHETIC: No real VIP labels in source data."""
    return random.choice(VIP_TIERS)


def _synthetic_priority() -> str:
    """SYNTHETIC: Used only when real priority is missing."""
    return random.choice(PRIORITIES)


def _synthetic_handle_time() -> float:
    """SYNTHETIC: No real handle times in source data."""
    return round(random.uniform(3.0, 90.0), 1)


def _synthetic_churn(priority: str, vip_tier: str) -> bool:
    """SYNTHETIC: No real churn labels in source data.
    Churn probability increases with priority and VIP tier.
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


# ---------------------------------------------------------------------------
# Build from support tickets (Dataset 1)
# ---------------------------------------------------------------------------

def build_from_tickets(max_cases: int = 25) -> list[CaseBundle]:
    """Build case bundles from support ticket JSONL.

    Real fields used: body, answer, priority, language, queue, type, tag_1..tag_8
    Synthetic fields: vip_tier, handle_time_minutes, churned_within_30d
    """
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
            is_synthetic = row.get("_synthetic", False)

            # --- REAL fields ---
            ticket_text = row.get("body") or row.get("subject") or ""
            if not ticket_text.strip():
                continue

            # Use real priority if valid, otherwise synthesize
            priority = (row.get("priority") or "").lower().strip()
            if priority not in ("low", "medium", "high", "critical"):
                priority = _synthetic_priority()

            # Use real language from dataset
            language = (row.get("language") or "").lower().strip()
            if not language:
                language = detect_language(ticket_text)

            # Use agent answer as conversation context (real)
            answer = row.get("answer", "")

            # Collect real tags for auditability
            real_tags = []
            for tag_key in ["queue", "type"] + [f"tag_{j}" for j in range(1, 9)]:
                val = row.get(tag_key)
                if val and str(val).strip():
                    real_tags.append(f"{tag_key}={val}")

            # Build subject line for richer ticket text
            subject = row.get("subject", "")
            if subject and subject not in ticket_text:
                ticket_text = f"[{subject}]\n{ticket_text}"

            # --- SYNTHETIC fields (explicitly marked) ---
            vip_tier = _synthetic_vip_tier()
            handle_time = _synthetic_handle_time()
            churned = _synthetic_churn(priority, vip_tier)

            case = CaseBundle(
                case_id=_make_case_id("ticket", i),
                ticket_text=ticket_text,
                conversation_snippet=answer,
                email_thread=[],
                vip_tier=vip_tier,
                priority=priority,
                handle_time_minutes=handle_time,
                churned_within_30d=churned,
                source_dataset="support_tickets" + (" (synthetic)" if is_synthetic else " (real)"),
                language=language,
            )
            cases.append(normalize_case(case))

    real_count = sum(1 for c in cases if "(real)" in c.source_dataset)
    synth_count = sum(1 for c in cases if "(synthetic)" in c.source_dataset)
    print(f"Built {len(cases)} cases from support tickets ({real_count} real, {synth_count} synthetic)")
    return cases


# ---------------------------------------------------------------------------
# Build from Bitext dialogues (Dataset 2)
# ---------------------------------------------------------------------------

def build_from_bitext(max_cases: int = 15) -> list[CaseBundle]:
    """Build case bundles from Bitext dialogue JSONL.

    Real fields used: instruction, response, category, intent
    Synthetic fields: vip_tier, handle_time_minutes, churned_within_30d, priority
    """
    bitext_path = RAW_DIR / "bitext_dialogues.jsonl"
    if not bitext_path.exists():
        print(f"Info: {bitext_path} not found. Trying legacy samsum_conversations.jsonl...")
        return _build_from_samsum_legacy(max_cases)

    cases = []
    with open(bitext_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_cases:
                break
            row = json.loads(line)
            is_synthetic = row.get("_synthetic", False)

            # --- REAL fields ---
            instruction = row.get("instruction", "")
            response = row.get("response", "")
            category = row.get("category", "").lower()
            intent = row.get("intent", "")

            if not instruction.strip():
                continue

            # Build ticket text from real category + instruction
            ticket_text = f"[{category.upper()}] {instruction}"

            # Build conversation from instruction/response pair
            conversation = f"Customer: {instruction}\nAgent: {response}"

            # Map category to priority heuristic
            high_priority_categories = {"refund", "cancellation_fee", "complaint"}
            priority = _synthetic_priority()
            if any(kw in intent.lower() for kw in ["complain", "refund", "cancel"]):
                priority = random.choice(["high", "critical"])

            # --- SYNTHETIC fields ---
            vip_tier = _synthetic_vip_tier()
            handle_time = _synthetic_handle_time()
            churned = _synthetic_churn(priority, vip_tier)

            case = CaseBundle(
                case_id=_make_case_id("bitext", i),
                ticket_text=ticket_text,
                conversation_snippet=conversation,
                email_thread=[],
                vip_tier=vip_tier,
                priority=priority,
                handle_time_minutes=handle_time,
                churned_within_30d=churned,
                source_dataset="bitext_dialogues" + (" (synthetic)" if is_synthetic else " (real)"),
                language="en",
            )
            cases.append(normalize_case(case))

    real_count = sum(1 for c in cases if "(real)" in c.source_dataset)
    synth_count = sum(1 for c in cases if "(synthetic)" in c.source_dataset)
    print(f"Built {len(cases)} cases from Bitext dialogues ({real_count} real, {synth_count} synthetic)")
    return cases


def _build_from_samsum_legacy(max_cases: int = 15) -> list[CaseBundle]:
    """Fallback: build from legacy samsum_conversations.jsonl if bitext is unavailable."""
    samsum_path = RAW_DIR / "samsum_conversations.jsonl"
    if not samsum_path.exists():
        print(f"Warning: No dialogue data found. Run scripts/ingest_data.py first.")
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
                source_dataset="samsum (synthetic)",
                language="en",
            )
            cases.append(normalize_case(case))

    print(f"Built {len(cases)} cases from SAMSum (legacy, all synthetic)")
    return cases


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_all_cases() -> list[CaseBundle]:
    """Build all case bundles and save to data/cases/."""
    CASES_DIR.mkdir(parents=True, exist_ok=True)

    # Clear existing cases
    for old in CASES_DIR.glob("*.json"):
        old.unlink()

    all_cases = []
    all_cases.extend(build_from_tickets(max_cases=25))
    all_cases.extend(build_from_bitext(max_cases=15))

    if not all_cases:
        print("ERROR: No cases built. Ensure raw data exists in data/raw/.")
        print("Run: python scripts/ingest_data.py")
        return []

    for case in all_cases:
        save_case_bundle(case, CASES_DIR)

    # Summary
    real_count = sum(1 for c in all_cases if "(real)" in c.source_dataset)
    synth_count = sum(1 for c in all_cases if "(synthetic)" in c.source_dataset)
    print(f"\nTotal: {len(all_cases)} case bundles saved to {CASES_DIR}/")
    print(f"  Real source data:      {real_count}")
    print(f"  Synthetic fallback:    {synth_count}")
    return all_cases


if __name__ == "__main__":
    build_all_cases()
