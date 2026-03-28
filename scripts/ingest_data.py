"""Download public datasets to data/raw/.

Downloads via HTTP API to avoid heavy dependency issues with the
`datasets` library. Falls back gracefully if network is unavailable.
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

RAW_DIR = Path("data/raw")


def ingest_support_tickets(max_rows: int = 200) -> Path:
    """Download support ticket dataset from HuggingFace via API.

    Saves a JSONL file to data/raw/support_tickets.jsonl
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "support_tickets.jsonl"

    url = (
        "https://datasets-server.huggingface.co/rows"
        "?dataset=Tobi-Bueck/customer-support-tickets"
        "&config=default&split=train"
        f"&offset=0&length={max_rows}"
    )

    print(f"Downloading support tickets (max {max_rows} rows)...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        rows = data.get("rows", [])
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for item in rows:
                row = item.get("row", item)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

        print(f"Saved {count} tickets to {output_path}")
        return output_path

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"Download failed: {e}")
        print("Creating synthetic fallback data...")
        return _create_synthetic_tickets(output_path, max_rows=min(max_rows, 30))


def ingest_samsum(max_rows: int = 100) -> Path:
    """Download SAMSum conversation dataset from HuggingFace via API.

    Saves a JSONL file to data/raw/samsum_conversations.jsonl
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / "samsum_conversations.jsonl"

    url = (
        "https://datasets-server.huggingface.co/rows"
        "?dataset=knkarthick/samsum"
        "&config=samsum&split=train"
        f"&offset=0&length={max_rows}"
    )

    print(f"Downloading SAMSum conversations (max {max_rows} rows)...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        rows = data.get("rows", [])
        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for item in rows:
                row = item.get("row", item)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

        print(f"Saved {count} conversations to {output_path}")
        return output_path

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"Download failed: {e}")
        print("Creating synthetic fallback data...")
        return _create_synthetic_conversations(output_path, max_rows=min(max_rows, 20))


def _create_synthetic_tickets(path: Path, max_rows: int = 30) -> Path:
    """Create synthetic support tickets as fallback."""
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
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    print(f"Created {count} synthetic tickets at {path}")
    return path


def _create_synthetic_conversations(path: Path, max_rows: int = 20) -> Path:
    """Create synthetic conversations as fallback."""
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
        {
            "dialogue": "Customer: The technician was supposed to come between 9-12 but never showed.\nAgent: I'm sorry about that. Let me check the appointment status.\nCustomer: I took time off work for this.\nAgent: I see the appointment was rescheduled without notification. That shouldn't happen.\nCustomer: I need this done this week.\nAgent: I've booked you for tomorrow 9 AM as the first appointment. I'll also apply a service credit.",
            "summary": "Technician no-show for scheduled appointment. Agent reschedules for next day first slot and applies service credit.",
        },
        {
            "dialogue": "Customer: My bill went up $30 this month with no explanation.\nAgent: Let me pull up your account details.\nCustomer: I've been a customer for 5 years and my rate has never changed.\nAgent: It appears your promotional discount expired last month.\nCustomer: Nobody told me it would expire. I want the discount back.\nAgent: I can offer you a loyalty discount of $20/month for the next 12 months.",
            "summary": "Long-term customer's bill increased $30 due to expired promo. Agent offers $20/month loyalty discount for 12 months.",
        },
        {
            "dialogue": "Customer: 我的网络一直很慢。\nAgent: I understand you're experiencing slow speeds. Let me run a diagnostic.\nCustomer: 已经三天了，我需要上网工作。\nAgent: I see there's congestion on your node. I can schedule a technician visit.\nCustomer: 什么时候能修好？\nAgent: We can have someone there by Thursday.",
            "summary": "Customer reports slow internet for 3 days in mixed Chinese-English conversation. Node congestion identified, technician visit scheduled for Thursday.",
        },
        {
            "dialogue": "Customer: I just want to say your new app update is terrible.\nAgent: I'm sorry you feel that way. What specific issues are you experiencing?\nCustomer: It crashes constantly and the new layout is confusing.\nAgent: We've received similar feedback. Our development team is working on a fix.\nCustomer: When will the fix be available?\nAgent: We expect a patch within the next two weeks.",
            "summary": "Customer complains about app crashes and confusing new layout. Agent acknowledges widespread issue and expects patch within two weeks.",
        },
        {
            "dialogue": "Customer: I need to set up autopay but your website won't let me.\nAgent: Let me help you with that. Are you getting an error message?\nCustomer: It says 'invalid payment method' but my card works everywhere else.\nAgent: It might be a system issue. I can set up autopay on my end for you.\nCustomer: That would be great.\nAgent: Done. Autopay is now active starting next month.",
            "summary": "Customer unable to set up autopay online due to system error. Agent manually enables autopay effective next billing cycle.",
        },
    ]

    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for conv in conversations[:max_rows]:
            f.write(json.dumps(conv, ensure_ascii=False) + "\n")
            count += 1

    print(f"Created {count} synthetic conversations at {path}")
    return path


if __name__ == "__main__":
    print("=== Ingesting public datasets ===")
    ingest_support_tickets()
    ingest_samsum()
    print("=== Done ===")
