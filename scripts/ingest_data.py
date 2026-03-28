"""Download public datasets to data/raw/.

Datasets:
- Support tickets from HuggingFace (Tobi-Bueck/customer-support-tickets)
- SAMSum conversations from HuggingFace (knkarthick/samsum)

No raw data is committed to the repo. This script downloads at runtime.
"""
import json
from pathlib import Path

RAW_DIR = Path("data/raw")


def ingest_support_tickets(max_rows: int = 200) -> Path:
    """Download support ticket dataset from HuggingFace.

    Saves a JSONL file to data/raw/support_tickets.jsonl
    """
    from datasets import load_dataset

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "support_tickets.jsonl"

    print(f"Downloading support tickets (max {max_rows} rows)...")
    ds = load_dataset("Tobi-Bueck/customer-support-tickets", split="train")

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for row in ds:
            if count >= max_rows:
                break
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    print(f"Saved {count} tickets to {output_path}")
    return output_path


def ingest_samsum(max_rows: int = 100) -> Path:
    """Download SAMSum conversation dataset from HuggingFace.

    Saves a JSONL file to data/raw/samsum_conversations.jsonl
    """
    from datasets import load_dataset

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "samsum_conversations.jsonl"

    print(f"Downloading SAMSum conversations (max {max_rows} rows)...")
    ds = load_dataset("knkarthick/samsum", split="train")

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for row in ds:
            if count >= max_rows:
                break
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    print(f"Saved {count} conversations to {output_path}")
    return output_path


if __name__ == "__main__":
    print("=== Ingesting public datasets ===")
    ingest_support_tickets()
    ingest_samsum()
    print("=== Done ===")
