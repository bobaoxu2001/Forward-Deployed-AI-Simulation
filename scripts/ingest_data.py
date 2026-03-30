"""Download public datasets to data/raw/.

Downloads via HTTP API to avoid heavy dependency issues with the
`datasets` library. Falls back gracefully if network is unavailable.

Datasets used:
  1. Tobi-Bueck/customer-support-tickets (CC BY-NC 4.0)
     - Real multilingual enterprise support tickets
     - Fields: subject, body, answer, type, queue, priority, language, tag_1..tag_8
  2. bitext/Bitext-customer-support-llm-chatbot-training-dataset (Apache 2.0)
     - Customer-agent dialogue pairs with intent/category labels
     - Fields: instruction, response, category, intent, flags
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

RAW_DIR = Path("data/raw")

HF_API_BASE = "https://datasets-server.huggingface.co/rows"


def _fetch_hf_rows(dataset: str, config: str, split: str,
                   offset: int = 0, length: int = 100,
                   retries: int = 2) -> list[dict]:
    """Fetch rows from HuggingFace datasets-server API.

    Returns list of row dicts. Retries on transient HTTP errors (422/5xx).
    """
    url = (
        f"{HF_API_BASE}"
        f"?dataset={dataset}"
        f"&config={config}&split={split}"
        f"&offset={offset}&length={length}"
    )
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (forward-deployed-ai-sim)",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [item.get("row", item) for item in data.get("rows", [])]
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code in (422, 429, 500, 502, 503) and attempt < retries:
                import time
                wait = 5 * (attempt + 1)  # 5s, 10s backoff
                print(f"    HTTP {e.code}, retrying in {wait}s (attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue
            raise
    raise last_error  # unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Dataset 1: Support tickets
# ---------------------------------------------------------------------------

def ingest_support_tickets(max_rows: int = 200) -> Path:
    """Download support ticket dataset from HuggingFace.

    Source: Tobi-Bueck/customer-support-tickets
    Saves JSONL to data/raw/support_tickets.jsonl
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "support_tickets.jsonl"

    # Skip if real data already exists
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            first_line = f.readline()
        if first_line and "_synthetic" not in first_line:
            line_count = sum(1 for _ in open(output_path))
            print(f"  ✓ Already have {line_count} REAL tickets at {output_path} (skipping)")
            return output_path

    print(f"Downloading support tickets (max {max_rows} rows)...")
    try:
        rows = _fetch_hf_rows(
            dataset="Tobi-Bueck/customer-support-tickets",
            config="default",
            split="train",
            offset=0,
            length=max_rows,
        )

        if not rows:
            raise ValueError("API returned 0 rows")

        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for row in rows:
                # Keep all fields from the real dataset
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

        print(f"  ✓ Saved {count} REAL tickets to {output_path}")
        _print_ticket_stats(rows)
        return output_path

    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, ValueError) as e:
        print(f"  ✗ Download failed: {e}")
        print("  → Creating synthetic fallback data...")
        return _create_synthetic_tickets(output_path, max_rows=min(max_rows, 30))


def _print_ticket_stats(rows: list[dict]) -> None:
    """Print summary stats for downloaded tickets."""
    languages = {}
    queues = {}
    for row in rows:
        lang = row.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1
        queue = row.get("queue", "unknown")
        queues[queue] = queues.get(queue, 0) + 1
    print(f"  Languages: {dict(sorted(languages.items(), key=lambda x: -x[1]))}")
    print(f"  Queues:    {dict(sorted(queues.items(), key=lambda x: -x[1]))}")


# ---------------------------------------------------------------------------
# Dataset 2: Bitext customer support dialogues
# ---------------------------------------------------------------------------

def ingest_bitext_dialogues(max_rows: int = 100) -> Path:
    """Download Bitext customer support dialogue dataset.

    Source: bitext/Bitext-customer-support-llm-chatbot-training-dataset
    Saves JSONL to data/raw/bitext_dialogues.jsonl

    The dataset is very repetitive within each intent (~100 paraphrases),
    so we sample sparsely across offsets to maximize category diversity.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "bitext_dialogues.jsonl"

    # Skip if real data already exists
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            first_line = f.readline()
        if first_line and "_synthetic" not in first_line:
            line_count = sum(1 for _ in open(output_path))
            print(f"  ✓ Already have {line_count} REAL dialogues at {output_path} (skipping)")
            return output_path

    # Sample at staggered offsets to get diverse categories/intents
    # Dataset has ~27k rows, categories include ORDER, ACCOUNT, PAYMENT,
    # DELIVERY, REFUND, FEEDBACK, CONTACT, INVOICE, CANCELLATION, etc.
    sample_offsets = [0, 1000, 2000, 3000, 4000, 5000, 7000, 9000,
                      11000, 13000, 15000, 17000, 19000, 21000, 24000]
    rows_per_offset = max(1, max_rows // len(sample_offsets))

    print(f"Downloading Bitext dialogues (max {max_rows} rows, sparse sampling)...")
    try:
        all_rows = []
        seen_intents = set()

        for offset in sample_offsets:
            if len(all_rows) >= max_rows:
                break
            batch = _fetch_hf_rows(
                dataset="bitext/Bitext-customer-support-llm-chatbot-training-dataset",
                config="default",
                split="train",
                offset=offset,
                length=rows_per_offset + 5,  # fetch a few extra to deduplicate
            )
            for row in batch:
                intent = row.get("intent", "")
                # Take at most one example per intent to maximize diversity
                if intent not in seen_intents and len(all_rows) < max_rows:
                    all_rows.append(row)
                    seen_intents.add(intent)

        if not all_rows:
            raise ValueError("API returned 0 rows")

        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for row in all_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

        print(f"  ✓ Saved {count} REAL dialogues to {output_path}")
        print(f"  Unique intents: {len(seen_intents)}")
        categories = {}
        for row in all_rows:
            cat = row.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        print(f"  Categories: {dict(sorted(categories.items(), key=lambda x: -x[1]))}")
        return output_path

    except (urllib.error.URLError, urllib.error.HTTPError,
            TimeoutError, ValueError) as e:
        print(f"  ✗ Download failed: {e}")
        print("  → Creating synthetic fallback conversations...")
        return _create_synthetic_conversations(
            RAW_DIR / "samsum_conversations.jsonl",
            max_rows=min(max_rows, 20),
        )


# ---------------------------------------------------------------------------
# Synthetic fallback (used only when API is unreachable)
# ---------------------------------------------------------------------------

def _create_synthetic_tickets(path: Path, max_rows: int = 30) -> Path:
    """Create synthetic support tickets as fallback.

    LABELED: all fields are synthetic. Used only when real data download fails.
    """
    import random
    random.seed(42)

    categories = [
        ("billing", "I was charged twice for my subscription this month. Please fix this immediately."),
        ("billing", "My invoice shows an incorrect amount. I should be on the $29/month plan but was charged $49."),
        ("billing", "I cancelled my service last month but I'm still being billed. This is unacceptable."),
        ("network", "My internet has been down for 3 days. I work from home and this is critical."),
        ("network", "The connection keeps dropping every 30 minutes. I've already restarted the router multiple times."),
        ("network", "Extremely slow speeds. I'm paying for 100Mbps but only getting 5Mbps."),
        ("account", "I can't log into my account. Password reset isn't working either."),
        ("account", "Please update my address and phone number on file."),
        ("account", "I want to upgrade my plan to premium. Can you help with that?"),
        ("service", "The technician didn't show up for my scheduled appointment today."),
        ("service", "I've been on hold for 45 minutes trying to reach support. This is terrible customer service."),
        ("service", "Your mobile app crashes every time I try to check my usage."),
        ("product", "The equipment you sent is defective. The power light keeps blinking red."),
        ("product", "I need a replacement remote control. Mine stopped working."),
        ("security", "I received a suspicious email claiming to be from your company asking for my password."),
        ("security", "Someone made unauthorized changes to my account. I think my account was compromised."),
        ("billing", "Why was I charged an early termination fee? I completed my contract period."),
        ("network", "No service in my area since the storm last week. When will it be restored?"),
        ("service", "Your automated system keeps disconnecting my calls before I can speak to anyone."),
        ("product", "The new modem you sent doesn't support my existing setup. I need a compatible one."),
        ("billing", "I was promised a promotional rate of $19.99 but my bill shows $39.99."),
        ("network", "WiFi doesn't reach my home office. Signal is very weak upstairs."),
        ("account", "I'm moving to a new address next month. How do I transfer my service?"),
        ("service", "The online chat support gave me wrong information and now my service is disrupted."),
        ("product", "Battery on the provided router dies after 2 hours. Need replacement."),
        ("billing", "I've been paying for premium channels I never ordered. Want a refund for the past 3 months."),
        ("network", "Complete outage in the downtown area. Multiple neighbors affected too."),
        ("security", "I noticed unknown devices connected to my account. Please secure it immediately."),
        ("service", "Scheduled maintenance was supposed to be overnight but it extended into business hours."),
        ("account", "I want to cancel my service effective end of this month. Please confirm."),
    ]

    priorities = ["low", "medium", "medium", "high", "critical"]
    answers = [
        "We apologize for the inconvenience. Our team is looking into this issue.",
        "Thank you for reaching out. We've escalated this to our technical team.",
        "We understand your frustration. A credit has been applied to your account.",
        "Our technician will visit your location within 24-48 hours.",
        "We've updated your account as requested. Changes will take effect immediately.",
    ]

    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for i, (category, text) in enumerate(categories[:max_rows]):
            row = {
                "subject": f"Issue with {category} - Ticket #{i+1000}",
                "body": text,
                "answer": random.choice(answers),
                "priority": random.choice(priorities),
                "queue": category,
                "type": "complaint" if "unacceptable" in text.lower() or "terrible" in text.lower() else "inquiry",
                "language": "en",
                "_synthetic": True,  # Explicit label
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    print(f"  Created {count} SYNTHETIC tickets at {path}")
    return path


def _create_synthetic_conversations(path: Path, max_rows: int = 20) -> Path:
    """Create synthetic conversations as fallback.

    LABELED: all fields are synthetic. Used only when real data download fails.
    """
    conversations = [
        {
            "dialogue": "Customer: Hi, my internet is not working.\nAgent: I'm sorry to hear that. Let me check your connection status.\nCustomer: It's been down since yesterday morning.\nAgent: I can see there's an outage in your area. Our team is working on it.\nCustomer: When will it be fixed?\nAgent: We expect it to be resolved within 24 hours.",
            "summary": "Customer reports internet outage since yesterday. Agent confirms area outage and estimates 24-hour resolution.",
        },
        {
            "dialogue": "Customer: I want to dispute a charge on my bill.\nAgent: I'd be happy to help. Which charge are you referring to?\nCustomer: There's a $15 fee labeled 'service adjustment' that I don't recognize.\nAgent: Let me look into that. It appears this was an error. I'll remove it.\nCustomer: Thank you. How long until I see the credit?\nAgent: The credit will appear on your next billing cycle.",
            "summary": "Customer disputes unknown $15 service adjustment fee. Agent identifies it as an error and applies credit for next billing cycle.",
        },
        {
            "dialogue": "Customer: I'm extremely frustrated. This is the third time I'm calling about the same issue.\nAgent: I sincerely apologize. Let me review your case history.\nCustomer: Every time I call, I get a different answer. Nobody seems to know what's going on.\nAgent: I understand your frustration. I'm going to escalate this to our senior team.\nCustomer: I want this resolved today or I'm switching providers.\nAgent: I've marked this as urgent. A supervisor will call you within 2 hours.",
            "summary": "Frustrated repeat caller threatens to switch providers. Agent escalates to supervisor with 2-hour callback commitment.",
        },
        {
            "dialogue": "Customer: Can I upgrade my plan without extending my contract?\nAgent: Yes, you can upgrade anytime. Would you like to see the available options?\nCustomer: What's the price difference for the premium tier?\nAgent: The premium tier is $20 more per month and includes additional features.\nCustomer: OK, let me think about it.\nAgent: No problem. I'll send you a comparison email.",
            "summary": "Customer inquires about plan upgrade pricing. Agent explains $20/month premium tier difference and will send comparison email.",
        },
        {
            "dialogue": "Customer: Someone accessed my account without permission.\nAgent: This is very concerning. Let me secure your account immediately.\nCustomer: I noticed charges I didn't make.\nAgent: I've temporarily locked your account. We'll need to verify your identity.\nCustomer: What charges were made?\nAgent: There are three unauthorized transactions totaling $127. We'll investigate and reverse them.",
            "summary": "Customer reports unauthorized account access with $127 in fraudulent charges. Agent locks account and initiates investigation to reverse transactions.",
        },
    ]

    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for conv in conversations[:max_rows]:
            conv["_synthetic"] = True
            f.write(json.dumps(conv, ensure_ascii=False) + "\n")
            count += 1

    print(f"  Created {count} SYNTHETIC conversations at {path}")
    return path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Data Ingestion — downloading public datasets")
    print("=" * 60)
    print()
    ingest_support_tickets(max_rows=200)
    print()
    ingest_bitext_dialogues(max_rows=100)
    print()
    print("=" * 60)
    print("Done. Raw data saved to data/raw/")
    print("Next step: python scripts/build_cases.py")
    print("=" * 60)
