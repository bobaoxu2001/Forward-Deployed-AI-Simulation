"""Page 3 — Reliability & Review: gate distribution, reason codes, confidence, case table."""
import sys
import json
import re
import sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from pipeline.storage import get_all_extractions, get_review_queue, get_trace_logs

st.set_page_config(page_title="Reliability & Review", layout="wide")
st.title("Reliability & Review")

DB_PATH = Path("data/processed/results.db")
REAL_EVAL_PATH = Path("data/eval/batch_10_real_provider.md")


# ---------------------------------------------------------------------------
# Helpers: parse real-eval markdown report
# ---------------------------------------------------------------------------

def _parse_real_eval_report() -> dict | None:
    """Parse the batch_10_real_provider.md report.

    Returns dict with:
      - "metrics": dict of metric name -> value string
      - "cases": list of dicts with per-case results
      - "case_ids": set of case_ids covered
    Returns None if file doesn't exist or can't be parsed.
    """
    if not REAL_EVAL_PATH.exists():
        return None

    try:
        text = REAL_EVAL_PATH.read_text(encoding="utf-8")
    except Exception:
        return None

    # Parse aggregate metrics table
    # Extract only lines between "## Aggregate Metrics" and next "---" divider
    metrics = {}
    agg_match = re.search(
        r"## Aggregate Metrics\s*\n(.*?)(?:\n---)", text, re.DOTALL
    )
    if agg_match:
        for line in agg_match.group(1).strip().split("\n"):
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 4:
                name = cols[0]
                # Skip header row and separator row
                if name in ("Metric", "") or name.startswith("-"):
                    continue
                # Skip if first col looks like a row number
                try:
                    int(name)
                    continue
                except ValueError:
                    pass
                metrics[name] = {"result": cols[1], "target": cols[2], "status": cols[3]}

    # Parse per-case results table
    cases = []
    cases_section = re.search(
        r"## Per-Case Results.*?\n\n((?:\|.*\n)+)", text, re.DOTALL
    )
    if cases_section:
        for line in cases_section.group(1).strip().split("\n"):
            cols = [c.strip() for c in line.split("|") if c.strip()]
            if len(cols) >= 9 and cols[0] not in ("#", "---", "-"):
                try:
                    int(cols[0])  # first col is row number
                except ValueError:
                    continue
                cases.append({
                    "case_id": cols[1],
                    "input_desc": cols[2],
                    "root_cause": cols[3],
                    "risk": cols[4],
                    "confidence": cols[5],
                    "gate": cols[6],
                    "evidence": cols[7],
                    "quality": cols[8],
                })

    if not metrics and not cases:
        return None

    return {
        "metrics": metrics,
        "cases": cases,
        "case_ids": {c["case_id"] for c in cases},
    }


def _get_trace_map() -> dict:
    """Build case_id -> trace metadata lookup."""
    traces = get_trace_logs()
    trace_map = {}
    for t in traces:
        cid = t.get("case_id")
        if cid and cid not in trace_map:  # keep most recent (already DESC)
            trace_map[cid] = t
    return trace_map


def _classify_source(case_id: str, real_eval_ids: set, trace_map: dict) -> str:
    """Classify result source for a case."""
    if case_id in real_eval_ids:
        return "real_eval"
    trace = trace_map.get(case_id)
    if trace:
        if trace.get("model_name", "unknown") == "unknown" and trace.get("latency_ms", 0) == 0:
            return "mock_db"
    return "unknown"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

if not DB_PATH.exists():
    st.warning("No pipeline results yet. Run `PYTHONPATH=. python scripts/run_pipeline.py --mock` first.")
    st.stop()

all_extractions = get_all_extractions()
review_queue = get_review_queue()
trace_map = _get_trace_map()
real_eval = _parse_real_eval_report()
real_eval_ids = real_eval["case_ids"] if real_eval else set()

if not all_extractions and not real_eval:
    st.info("No extractions in database and no real evaluation report found.")
    st.stop()


# ---------------------------------------------------------------------------
# Data provenance warning
# ---------------------------------------------------------------------------

has_mock = any(
    _classify_source(e["case_id"], real_eval_ids, trace_map) == "mock_db"
    for e in all_extractions
)

if has_mock and real_eval:
    st.info(
        "**Data provenance note:** The database contains **stale mock extractions** "
        f"({len(all_extractions)} cases, MockProvider). A separate **real-model batch evaluation** "
        f"exists covering {len(real_eval_ids)} cases (Claude Sonnet). "
        "Both are shown below with clear labels. This page is an inspection tool, "
        "not the final source of truth for model quality."
    )
elif has_mock:
    st.warning(
        "**Data provenance note:** All database extractions are from **MockProvider** "
        "(fixed output, no real LLM). Metrics below reflect pipeline plumbing, not model quality. "
        "Run a real-provider evaluation to get meaningful reliability metrics."
    )


# ---------------------------------------------------------------------------
# Section 1: Real-eval metrics (if available)
# ---------------------------------------------------------------------------

if real_eval and real_eval["metrics"]:
    st.header("Real-Model Evaluation Metrics")
    st.caption(
        f"Source: `data/eval/batch_10_real_provider.md` · "
        f"Model: claude-sonnet-4-20250514 · {len(real_eval_ids)} cases"
    )

    metrics = real_eval["metrics"]
    mcols = st.columns(len(metrics))
    for i, (name, vals) in enumerate(metrics.items()):
        with mcols[i]:
            status = vals["status"]
            if status == "PASS":
                st.metric(name, vals["result"])
                st.caption(f"Target: {vals['target']} · :green[PASS]")
            elif status == "MARGINAL":
                st.metric(name, vals["result"])
                st.caption(f"Target: {vals['target']} · :orange[MARGINAL]")
            elif status == "—":
                st.metric(name, vals["result"])
                st.caption("informational")
            else:
                st.metric(name, vals["result"])
                st.caption(f"Target: {vals['target']} · :red[{status}]")

    st.divider()


# ---------------------------------------------------------------------------
# Section 2: DB snapshot metrics
# ---------------------------------------------------------------------------

st.header("Database Snapshot Metrics")
st.caption(
    f"Source: SQLite `results.db` · {len(all_extractions)} extractions · "
    + ("mostly mock data" if has_mock else "mixed sources")
)

# Compute metrics from DB
auto_count = sum(1 for e in all_extractions if e.get("gate_route") == "auto")
review_count = len(all_extractions) - auto_count
confidences = [e.get("confidence", 0) for e in all_extractions if e.get("confidence") is not None]
avg_conf = sum(confidences) / len(confidences) if confidences else 0

latencies = [t.get("latency_ms", 0) for t in trace_map.values() if t.get("latency_ms") is not None]
avg_latency = sum(latencies) / len(latencies) if latencies else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Cases", len(all_extractions))
m2.metric("Review", review_count)
m3.metric("Auto", auto_count)
m4.metric("Avg Confidence", f"{avg_conf:.2f}")
m5.metric("Avg Latency", f"{avg_latency:.0f} ms")


# ---------------------------------------------------------------------------
# Section 3: Reason code breakdown
# ---------------------------------------------------------------------------

st.divider()
st.header("Reason Code Breakdown")

from collections import Counter
reason_counts = Counter()
for ext in all_extractions:
    codes = ext.get("review_reason_codes", "[]")
    if isinstance(codes, str):
        try:
            codes = json.loads(codes)
        except (json.JSONDecodeError, TypeError):
            codes = []
    for code in codes:
        reason_counts[code] += 1

# Also count from real eval if available
real_eval_reason_counts = Counter()
if real_eval:
    for c in real_eval["cases"]:
        gate_str = c.get("gate", "")
        # Parse "review (4 codes)" -> we need the actual codes from the report
        # The per-case table doesn't list codes, but the detailed section does.
        # For now, just count review vs auto.
        pass

if reason_counts:
    reason_df = pd.DataFrame(
        [{"Reason Code": k, "Count": v} for k, v in reason_counts.most_common()],
    )
    st.bar_chart(reason_df.set_index("Reason Code"))
else:
    st.info(
        "No review reason codes in database. "
        "This is expected with mock data — MockProvider returns fixed 'billing' "
        "output that passes all gate rules."
    )


# ---------------------------------------------------------------------------
# Section 4: Confidence distribution
# ---------------------------------------------------------------------------

st.divider()
st.header("Confidence Distribution")

if confidences:
    conf_df = pd.DataFrame({"confidence": confidences})
    st.bar_chart(conf_df["confidence"].value_counts(bins=10).sort_index())
    if has_mock and len(set(confidences)) <= 2:
        st.caption(
            "Note: All values are identical because MockProvider returns a fixed confidence score."
        )
else:
    st.info("No confidence scores recorded.")


# ---------------------------------------------------------------------------
# Section 5: All cases table
# ---------------------------------------------------------------------------

st.divider()
st.header("All Cases")

# Join extractions with case metadata from DB
case_meta = {}
if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    for row in conn.execute("SELECT case_id, language, priority, source_dataset FROM cases"):
        r = dict(row)
        case_meta[r["case_id"]] = r
    conn.close()

table_rows = []

# Add DB extractions
for ext in all_extractions:
    cid = ext["case_id"]
    meta = case_meta.get(cid, {})
    source = _classify_source(cid, real_eval_ids, trace_map)

    codes = ext.get("review_reason_codes", "[]")
    if isinstance(codes, str):
        try:
            codes = json.loads(codes)
        except (json.JSONDecodeError, TypeError):
            codes = []

    table_rows.append({
        "Case ID": cid,
        "Result Source": source,
        "Source Dataset": meta.get("source_dataset", "—"),
        "Language": meta.get("language", "—"),
        "Priority": meta.get("priority", "—"),
        "Root Cause": ext.get("root_cause_l1", "—"),
        "Risk": ext.get("risk_level", "—"),
        "Confidence": ext.get("confidence", 0),
        "Gate": ext.get("gate_route", "—"),
        "Reason Codes": ", ".join(codes) if codes else "—",
    })

# Add real-eval cases NOT already in DB
if real_eval:
    db_ids = {e["case_id"] for e in all_extractions}
    for c in real_eval["cases"]:
        if c["case_id"] not in db_ids:
            table_rows.append({
                "Case ID": c["case_id"],
                "Result Source": "real_eval",
                "Source Dataset": "—",
                "Language": "—",
                "Priority": "—",
                "Root Cause": c.get("root_cause", "—"),
                "Risk": c.get("risk", "—"),
                "Confidence": float(c.get("confidence", 0)),
                "Gate": "review" if "review" in c.get("gate", "") else "auto",
                "Reason Codes": "—",
            })

if table_rows:
    table_df = pd.DataFrame(table_rows)
    st.dataframe(table_df, use_container_width=True, hide_index=True)
else:
    st.info("No case data available.")


# ---------------------------------------------------------------------------
# Section 6: Examples — review vs auto
# ---------------------------------------------------------------------------

st.divider()

col_review, col_auto = st.columns(2)

# Separate by gate decision
review_examples = [r for r in table_rows if r["Gate"] == "review"]
auto_examples = [r for r in table_rows if r["Gate"] == "auto"]

with col_review:
    st.subheader(f"Examples Routed to Review ({len(review_examples)})")

    if not review_examples:
        st.info(
            "No cases routed to review in current data. "
            "This is expected with mock data — MockProvider output (billing, "
            "confidence=0.85, risk=medium) passes all gate rules."
        )
    else:
        for ex in review_examples[:3]:
            source_tag = f"`{ex['Result Source']}`"
            st.markdown(
                f"**{ex['Case ID']}** {source_tag}  \n"
                f"Root cause: `{ex['Root Cause']}` · Risk: `{ex['Risk']}` · "
                f"Confidence: {ex['Confidence']}  \n"
                f"Reason codes: {ex['Reason Codes']}"
            )
            st.markdown("---")

        if len(review_examples) > 3:
            st.caption(f"+ {len(review_examples) - 3} more in table above")

with col_auto:
    st.subheader(f"Examples Safe for Auto-Routing ({len(auto_examples)})")

    if not auto_examples:
        st.info("No cases auto-routed in current data.")
    else:
        for ex in auto_examples[:3]:
            source_tag = f"`{ex['Result Source']}`"
            st.markdown(
                f"**{ex['Case ID']}** {source_tag}  \n"
                f"Root cause: `{ex['Root Cause']}` · Risk: `{ex['Risk']}` · "
                f"Confidence: {ex['Confidence']}  \n"
                f"No review triggers — all gate rules passed."
            )
            st.markdown("---")

        if len(auto_examples) > 3:
            st.caption(f"+ {len(auto_examples) - 3} more in table above")


# ---------------------------------------------------------------------------
# Section 7: Review rules reference
# ---------------------------------------------------------------------------

st.divider()
st.header("Review Rules Reference")
st.caption("These rules are encoded in `pipeline/gate.py`. Any match triggers human review.")

st.markdown("""
| # | Rule | Trigger | Reason Code |
|---|------|---------|-------------|
| 1 | Low confidence | confidence < 0.7 | `low_confidence` |
| 2 | High churn risk | churn_risk >= 0.6 | `high_churn_risk` |
| 3 | High risk level | risk = high or critical | `high_risk_level` |
| 4 | Model flagged | review_required = true | `model_flagged` |
| 5 | High-risk category | security_breach, outage, vip_churn, data_loss | `high_risk_category` |
| 6 | Missing evidence | evidence_quotes empty | `missing_evidence` |
| 7 | Ambiguous root cause | root_cause = unknown / ambiguous / other | `ambiguous_root_cause` |
""")
