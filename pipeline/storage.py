"""Storage layer: SQLite for queryable data, JSONL for trace logs.

Three tables:
- cases: raw case bundle data
- extractions: structured LLM outputs
- trace_logs: full audit trail per pipeline run
"""
import json
import sqlite3
import time
from pathlib import Path

from pipeline.schemas import CaseBundle, ExtractionOutput

DB_PATH = Path("data/processed/results.db")
TRACE_LOG_PATH = Path("data/processed/trace.jsonl")


def _get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection, creating parent dirs if needed."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create all tables if they don't exist."""
    conn = _get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                ticket_text TEXT NOT NULL,
                email_thread TEXT,
                conversation_snippet TEXT,
                vip_tier TEXT,
                priority TEXT,
                handle_time_minutes REAL,
                churned_within_30d INTEGER,
                source_dataset TEXT,
                language TEXT,
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS extractions (
                case_id TEXT PRIMARY KEY,
                root_cause_l1 TEXT,
                root_cause_l2 TEXT,
                sentiment_score REAL,
                risk_level TEXT,
                review_required INTEGER,
                next_best_actions TEXT,
                evidence_quotes TEXT,
                confidence REAL,
                churn_risk REAL,
                sentiment_rationale TEXT,
                draft_notes TEXT,
                gate_route TEXT,
                gate_reasons TEXT,
                review_reason_codes TEXT,
                created_at REAL,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            );

            CREATE TABLE IF NOT EXISTS trace_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                timestamp REAL,
                model_name TEXT,
                prompt_version TEXT,
                validation_pass INTEGER,
                validation_errors TEXT,
                review_required INTEGER,
                review_reason_codes TEXT,
                gate_route TEXT,
                latency_ms REAL,
                raw_response TEXT,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            );
        """)
        conn.commit()
    finally:
        conn.close()


def store_case(case: CaseBundle, db_path: Path | None = None) -> None:
    """Insert or replace a case bundle in the cases table."""
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO cases
            (case_id, ticket_text, email_thread, conversation_snippet,
             vip_tier, priority, handle_time_minutes, churned_within_30d,
             source_dataset, language, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case.case_id,
                case.ticket_text,
                json.dumps(case.email_thread),
                case.conversation_snippet,
                case.vip_tier,
                case.priority,
                case.handle_time_minutes,
                int(case.churned_within_30d),
                case.source_dataset,
                case.language,
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def store_extraction(
    case_id: str,
    extraction: ExtractionOutput,
    gate_decision: dict,
    db_path: Path | None = None,
) -> None:
    """Insert or replace an extraction result."""
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO extractions
            (case_id, root_cause_l1, root_cause_l2, sentiment_score,
             risk_level, review_required, next_best_actions, evidence_quotes,
             confidence, churn_risk, sentiment_rationale, draft_notes,
             gate_route, gate_reasons, review_reason_codes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                extraction.root_cause_l1,
                extraction.root_cause_l2,
                extraction.sentiment_score,
                extraction.risk_level,
                int(extraction.review_required),
                json.dumps(extraction.next_best_actions),
                json.dumps(extraction.evidence_quotes),
                extraction.confidence,
                extraction.churn_risk,
                extraction.sentiment_rationale,
                extraction.draft_notes,
                gate_decision["route"],
                json.dumps(gate_decision["reasons"]),
                json.dumps(gate_decision.get("review_reason_codes", [])),
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def store_trace_log(
    case_id: str,
    model_name: str,
    prompt_version: str,
    validation_pass: bool,
    validation_errors: list[str],
    review_required: bool,
    review_reason_codes: list[str],
    gate_route: str,
    latency_ms: float,
    raw_response: str,
    db_path: Path | None = None,
) -> None:
    """Insert a trace log entry into SQLite."""
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO trace_logs
            (case_id, timestamp, model_name, prompt_version,
             validation_pass, validation_errors, review_required,
             review_reason_codes, gate_route, latency_ms, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                time.time(),
                model_name,
                prompt_version,
                int(validation_pass),
                json.dumps(validation_errors),
                int(review_required),
                json.dumps(review_reason_codes),
                gate_route,
                latency_ms,
                raw_response,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def write_trace_jsonl(
    case_id: str,
    extraction: ExtractionOutput,
    gate_decision: dict,
    metadata: dict,
    validation_result: tuple[bool, list[str]],
) -> None:
    """Append a trace entry to the JSONL log file."""
    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.time(),
        "case_id": case_id,
        "model_name": metadata.get("model_name", "unknown"),
        "prompt_version": metadata.get("prompt_version", "unknown"),
        "latency_ms": metadata.get("latency_ms", 0),
        "validation_pass": validation_result[0],
        "validation_errors": validation_result[1],
        "gate_route": gate_decision["route"],
        "gate_reasons": gate_decision["reasons"],
        "review_reason_codes": gate_decision.get("review_reason_codes", []),
        "extraction": extraction.to_dict(),
    }
    with open(TRACE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- Query helpers ---

def get_all_extractions(db_path: Path | None = None) -> list[dict]:
    """Load all extraction results from SQLite."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM extractions").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_review_queue(db_path: Path | None = None) -> list[dict]:
    """Load cases routed to human review."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM extractions WHERE gate_route = 'review'"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_trace_logs(db_path: Path | None = None) -> list[dict]:
    """Load all trace log entries."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM trace_logs ORDER BY timestamp DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
