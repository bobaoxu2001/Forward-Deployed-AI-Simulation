"""Storage layer: SQLite for queryable aggregates, JSONL for trace logs."""
import json
import sqlite3
import hashlib
import time
from pathlib import Path


TRACE_LOG_PATH = Path("data/processed/trace.jsonl")
DB_PATH = Path("data/processed/results.db")


def write_trace_log(
    case_id: str,
    prompt_hash: str,
    model_id: str,
    output: dict,
    validation_result: tuple[bool, list[str]],
    gate_decision: dict,
    latency_ms: float,
):
    """Append a trace log entry to the JSONL file."""
    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.time(),
        "case_id": case_id,
        "prompt_hash": prompt_hash,
        "model_id": model_id,
        "output": output,
        "schema_valid": validation_result[0],
        "validation_errors": validation_result[1],
        "gate_route": gate_decision["route"],
        "gate_reasons": gate_decision["reasons"],
        "latency_ms": latency_ms,
    }
    with open(TRACE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def init_db():
    """Initialize SQLite database with results table."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            case_id TEXT PRIMARY KEY,
            root_cause_l1 TEXT,
            root_cause_l2 TEXT,
            confidence REAL,
            sentiment_score REAL,
            churn_risk REAL,
            severity TEXT,
            review_required INTEGER,
            gate_route TEXT,
            output_json TEXT,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()


def store_result(case_id: str, output: dict, gate_decision: dict):
    """Write a structured result to SQLite."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT OR REPLACE INTO results
        (case_id, root_cause_l1, root_cause_l2, confidence,
         sentiment_score, churn_risk, severity, review_required,
         gate_route, output_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            output.get("root_cause", {}).get("l1"),
            output.get("root_cause", {}).get("l2"),
            output.get("root_cause", {}).get("confidence"),
            output.get("sentiment", {}).get("score"),
            output.get("risk", {}).get("churn_risk"),
            output.get("risk", {}).get("severity"),
            int(output.get("risk", {}).get("review_required", False)),
            gate_decision["route"],
            json.dumps(output),
            time.time(),
        ),
    )
    conn.commit()
    conn.close()
