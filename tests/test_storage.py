"""Tests for SQLite storage layer."""
import tempfile
from pathlib import Path

from pipeline.schemas import CaseBundle, ExtractionOutput
from pipeline.storage import (
    init_db,
    store_case,
    store_extraction,
    store_trace_log,
    get_all_extractions,
    get_review_queue,
    get_trace_logs,
)


def _tmp_db():
    """Create a temporary database path."""
    tmpdir = tempfile.mkdtemp()
    return Path(tmpdir) / "test.db"


def test_init_db_creates_tables():
    db = _tmp_db()
    init_db(db)
    import sqlite3

    conn = sqlite3.connect(db)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {t[0] for t in tables}
    assert "cases" in table_names
    assert "extractions" in table_names
    assert "trace_logs" in table_names
    conn.close()


def test_store_and_retrieve_case():
    db = _tmp_db()
    init_db(db)
    case = CaseBundle(case_id="st-001", ticket_text="Test ticket")
    store_case(case, db)

    import sqlite3

    conn = sqlite3.connect(db)
    row = conn.execute("SELECT * FROM cases WHERE case_id='st-001'").fetchone()
    assert row is not None
    assert row[1] == "Test ticket"  # ticket_text
    conn.close()


def test_store_and_retrieve_extraction():
    db = _tmp_db()
    init_db(db)

    case = CaseBundle(case_id="st-002", ticket_text="Test")
    store_case(case, db)

    ext = ExtractionOutput(
        root_cause_l1="network",
        root_cause_l2="outage",
        sentiment_score=-0.8,
        risk_level="critical",
        review_required=True,
        next_best_actions=["Dispatch tech"],
        evidence_quotes=["internet down 3 days"],
        confidence=0.6,
        churn_risk=0.7,
    )
    gate = {
        "route": "review",
        "reasons": ["High risk"],
        "review_reason_codes": ["high_risk_level"],
    }
    store_extraction("st-002", ext, gate, db)

    results = get_all_extractions(db)
    assert len(results) == 1
    assert results[0]["case_id"] == "st-002"
    assert results[0]["root_cause_l1"] == "network"
    assert results[0]["gate_route"] == "review"


def test_review_queue_filters():
    db = _tmp_db()
    init_db(db)

    # Auto-routed case
    case1 = CaseBundle(case_id="auto-1", ticket_text="Simple question")
    store_case(case1, db)
    ext1 = ExtractionOutput(root_cause_l1="billing", risk_level="low")
    store_extraction("auto-1", ext1, {"route": "auto", "reasons": [], "review_reason_codes": []}, db)

    # Review-routed case
    case2 = CaseBundle(case_id="review-1", ticket_text="Major outage")
    store_case(case2, db)
    ext2 = ExtractionOutput(root_cause_l1="outage", risk_level="critical", review_required=True)
    store_extraction("review-1", ext2, {"route": "review", "reasons": ["High risk"], "review_reason_codes": ["high_risk_level"]}, db)

    queue = get_review_queue(db)
    assert len(queue) == 1
    assert queue[0]["case_id"] == "review-1"


def test_trace_log_storage():
    db = _tmp_db()
    init_db(db)

    store_trace_log(
        case_id="tr-001",
        model_name="claude-test",
        prompt_version="v1",
        validation_pass=True,
        validation_errors=[],
        review_required=False,
        review_reason_codes=[],
        gate_route="auto",
        latency_ms=150.5,
        raw_response='{"test": true}',
        db_path=db,
    )

    logs = get_trace_logs(db)
    assert len(logs) == 1
    assert logs[0]["case_id"] == "tr-001"
    assert logs[0]["model_name"] == "claude-test"
    assert logs[0]["latency_ms"] == 150.5
