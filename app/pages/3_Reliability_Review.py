"""Page 3 — Reliability & Review: review queue, reason codes, confidence, failure modes."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from pipeline.storage import get_all_extractions, get_review_queue, get_trace_logs

st.set_page_config(page_title="Reliability & Review", layout="wide")
st.title("Reliability & Review")

db_path = Path("data/processed/results.db")
if not db_path.exists():
    st.warning("No pipeline results yet. Run `python scripts/run_pipeline.py --mock` first.")
    st.stop()

# --- Load data ---
all_extractions = get_all_extractions()
review_queue = get_review_queue()
trace_logs = get_trace_logs()

if not all_extractions:
    st.info("No extractions in database. Run the pipeline first.")
    st.stop()

# --- Summary metrics ---
st.header("Gate Distribution")
c1, c2, c3 = st.columns(3)
c1.metric("Total Cases", len(all_extractions))
c2.metric("Auto-Routed", len(all_extractions) - len(review_queue))
c3.metric("Review Queue", len(review_queue))

# --- Review reason codes ---
st.header("Review Reason Codes")
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

if reason_counts:
    reason_df = pd.DataFrame(
        [{"Reason Code": k, "Count": v} for k, v in reason_counts.most_common()],
    )
    st.bar_chart(reason_df.set_index("Reason Code"))
else:
    st.info("No review reasons recorded.")

# --- Confidence distribution ---
st.header("Confidence Distribution")
confidences = [ext.get("confidence", 0) for ext in all_extractions if ext.get("confidence") is not None]
if confidences:
    conf_df = pd.DataFrame({"confidence": confidences})
    st.bar_chart(conf_df["confidence"].value_counts(bins=10).sort_index())
else:
    st.info("No confidence scores recorded.")

# --- Review queue detail ---
st.header("Cases Requiring Review")
if review_queue:
    review_df = pd.DataFrame([{
        "Case ID": r["case_id"],
        "Root Cause": r.get("root_cause_l1", ""),
        "Risk Level": r.get("risk_level", ""),
        "Confidence": r.get("confidence", 0),
        "Churn Risk": r.get("churn_risk", 0),
        "Gate Reasons": r.get("gate_reasons", ""),
        "Reason Codes": r.get("review_reason_codes", ""),
    } for r in review_queue])
    st.dataframe(review_df, use_container_width=True, hide_index=True)

    # Detail view
    selected_review = st.selectbox(
        "Inspect review case",
        [r["case_id"] for r in review_queue],
    )
    if selected_review:
        detail = next(r for r in review_queue if r["case_id"] == selected_review)
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Extraction")
            st.json({
                "root_cause_l1": detail.get("root_cause_l1"),
                "root_cause_l2": detail.get("root_cause_l2"),
                "sentiment_score": detail.get("sentiment_score"),
                "risk_level": detail.get("risk_level"),
                "confidence": detail.get("confidence"),
                "churn_risk": detail.get("churn_risk"),
            })
        with col_b:
            st.subheader("Review Decision")
            reasons = detail.get("gate_reasons", "[]")
            if isinstance(reasons, str):
                try:
                    reasons = json.loads(reasons)
                except (json.JSONDecodeError, TypeError):
                    reasons = [reasons]
            for r in reasons:
                st.markdown(f"- {r}")
else:
    st.success("No cases in review queue.")

# --- Trace logs ---
st.header("Audit Trail (Recent)")
if trace_logs:
    log_df = pd.DataFrame([{
        "Case ID": t["case_id"],
        "Model": t.get("model_name", ""),
        "Prompt": t.get("prompt_version", ""),
        "Schema Pass": bool(t.get("validation_pass", False)),
        "Route": t.get("gate_route", ""),
        "Latency (ms)": t.get("latency_ms", 0),
    } for t in trace_logs[:20]])
    st.dataframe(log_df, use_container_width=True, hide_index=True)
else:
    st.info("No trace logs recorded.")

# --- Failure mode rules ---
st.header("Review Rules (Encoded)")
st.markdown("""
| Rule | Trigger | Action |
|------|---------|--------|
| Low confidence | confidence < 0.7 | Route to review |
| High churn risk | churn_risk >= 0.6 | Route to review |
| High risk level | risk = high/critical | Route to review |
| Missing evidence | evidence_quotes empty | Route to review + flag |
| High-risk category | security_breach, outage, vip_churn, data_loss | Route to review |
| Ambiguous root cause | root_cause = unknown/ambiguous/other | Route to review |
| Model flagged | review_required = true | Route to review |
""")
