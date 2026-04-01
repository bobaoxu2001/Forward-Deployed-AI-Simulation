"""Page 5 — Executive Summary: C-suite view of operational insight.

This page answers the questions a COO/CXO actually asks:
- What are the top drivers of VIP churn?
- How much of our review workload can be automated?
- Where should we intervene first?
"""
import sys
import json
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from pipeline.storage import get_all_extractions, get_review_queue

st.set_page_config(page_title="Executive Summary", layout="wide")

DB_PATH = Path("data/processed/results.db")

if not DB_PATH.exists():
    st.warning("No pipeline results yet. Run `PYTHONPATH=. python scripts/run_pipeline.py --mock` first.")
    st.stop()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

cases = [dict(r) for r in conn.execute("SELECT * FROM cases").fetchall()]
extractions = [dict(r) for r in conn.execute("SELECT * FROM extractions").fetchall()]

# Join cases + extractions
case_map = {c["case_id"]: c for c in cases}
joined = []
for ext in extractions:
    c = case_map.get(ext["case_id"], {})
    joined.append({**c, **ext})

conn.close()

if not joined:
    st.info("No data available. Run the pipeline first.")
    st.stop()

df = pd.DataFrame(joined)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Executive Summary")
st.markdown(
    "One-glance operational intelligence for leadership. "
    "Every number below is backed by structured extraction with evidence citations — "
    "not manual tagging."
)
st.markdown("---")

# ---------------------------------------------------------------------------
# KPI Row: the 4 numbers a COO cares about
# ---------------------------------------------------------------------------

total_cases = len(df)
auto_count = len(df[df["gate_route"] == "auto"])
review_count = total_cases - auto_count
automation_rate = auto_count / total_cases if total_cases else 0
churn_cases = len(df[df["churned_within_30d"] == 1])
churn_rate = churn_cases / total_cases if total_cases else 0
vip_cases = len(df[df["vip_tier"] == "vip"]) if "vip_tier" in df.columns else 0
avg_handle = df["handle_time_minutes"].mean() if "handle_time_minutes" in df.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Automation Rate", f"{automation_rate:.0%}",
           help="% of cases safely auto-routed without human review")
k2.metric("Cases in Review Queue", f"{review_count}",
           help="Cases flagged for human review by gate logic")
k3.metric("30-Day Churn Rate", f"{churn_rate:.0%}",
           help="% of customers who churned within 30 days")
k4.metric("Avg Handle Time", f"{avg_handle:.0f} min",
           help="Average time from ticket open to resolution")

st.markdown("---")

# ---------------------------------------------------------------------------
# Section 1: Top Churn Drivers
# ---------------------------------------------------------------------------

st.header("Top Churn Drivers")
st.caption("Root causes most associated with customer churn — ranked by frequency among churned accounts")

churned_df = df[df["churned_within_30d"] == 1]

if len(churned_df) > 0 and "root_cause_l1" in churned_df.columns:
    churn_drivers = churned_df["root_cause_l1"].value_counts().reset_index()
    churn_drivers.columns = ["Root Cause", "Churned Cases"]
    churn_drivers["% of Churn"] = (churn_drivers["Churned Cases"] / len(churned_df) * 100).round(1)

    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        st.bar_chart(churn_drivers.set_index("Root Cause")["Churned Cases"])
    with col_table:
        st.dataframe(churn_drivers, hide_index=True, use_container_width=True)
else:
    st.info("No churned cases in current dataset to analyze drivers.")

# ---------------------------------------------------------------------------
# Section 2: VIP Risk Heat Map
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("VIP Risk Overview")
st.caption("VIP customers by risk level and churn status — where to intervene first")

if "vip_tier" in df.columns and "risk_level" in df.columns:
    vip_df = df[df["vip_tier"] == "vip"]
    if len(vip_df) > 0:
        vip_summary = vip_df.groupby(["risk_level", "churned_within_30d"]).size().reset_index(name="Count")
        vip_summary["Churn Status"] = vip_summary["churned_within_30d"].map({0: "Retained", 1: "Churned"})

        v1, v2, v3 = st.columns(3)
        v1.metric("Total VIP Cases", len(vip_df))
        vip_churned = len(vip_df[vip_df["churned_within_30d"] == 1])
        v2.metric("VIP Churned", vip_churned)
        vip_high_risk = len(vip_df[vip_df["risk_level"].isin(["high", "critical"])])
        v3.metric("VIP High/Critical Risk", vip_high_risk)

        # Cross-tab: risk level × churn
        if len(vip_df) > 1:
            cross = pd.crosstab(vip_df["risk_level"], vip_df["churned_within_30d"].map({0: "Retained", 1: "Churned"}))
            st.dataframe(cross, use_container_width=True)
    else:
        st.info("No VIP cases in current dataset.")
else:
    st.info("VIP tier data not available.")

# ---------------------------------------------------------------------------
# Section 3: Priority × Risk Distribution
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Priority vs. Risk Alignment")
st.caption("Are high-priority tickets actually high-risk? Misalignment = triage failure")

if "priority" in df.columns and "risk_level" in df.columns:
    priority_order = ["low", "medium", "high", "critical"]
    risk_order = ["low", "medium", "high", "critical"]

    cross_pr = pd.crosstab(
        df["priority"].astype(pd.CategoricalDtype(priority_order, ordered=True)),
        df["risk_level"].astype(pd.CategoricalDtype(risk_order, ordered=True)),
    )
    st.dataframe(cross_pr, use_container_width=True)

    # Flag misalignments
    misaligned = df[
        ((df["priority"] == "low") & (df["risk_level"].isin(["high", "critical"]))) |
        ((df["priority"] == "critical") & (df["risk_level"] == "low"))
    ]
    if len(misaligned) > 0:
        st.warning(
            f"**{len(misaligned)} cases** show priority/risk misalignment. "
            "These are either under-prioritized high-risk tickets or over-prioritized low-risk ones. "
            "Review recommended."
        )

# ---------------------------------------------------------------------------
# Section 4: Review Queue Breakdown
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Review Queue Analysis")
st.caption("Why are cases going to human review? Understanding trigger patterns optimizes staffing")

review_df = df[df["gate_route"] == "review"]

if len(review_df) > 0:
    from collections import Counter
    reason_counts = Counter()
    for _, row in review_df.iterrows():
        codes = row.get("review_reason_codes", "[]")
        if isinstance(codes, str):
            try:
                codes = json.loads(codes)
            except (json.JSONDecodeError, TypeError):
                codes = []
        for code in codes:
            reason_counts[code] += 1

    if reason_counts:
        reason_df = pd.DataFrame(
            [{"Trigger Rule": k, "Cases Triggered": v} for k, v in reason_counts.most_common()]
        )
        st.bar_chart(reason_df.set_index("Trigger Rule"))
        st.dataframe(reason_df, hide_index=True, use_container_width=True)
    else:
        st.info("Review cases present but no reason codes recorded.")
else:
    st.info(
        "All cases auto-routed (0 in review queue). "
        "With mock data, the fixed extraction output passes all gate rules. "
        "Run with a real provider to see meaningful review routing."
    )

# ---------------------------------------------------------------------------
# Section 5: Operational Efficiency Summary
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Operational Efficiency")

# Time savings estimate
MANUAL_MINUTES_PER_TICKET = 15  # industry benchmark: manual read + tag + route
AI_MINUTES_PER_TICKET = 0.5     # AI extraction + human spot-check for auto-routed
REVIEW_MINUTES_PER_TICKET = 5   # human review with AI pre-analysis

manual_total = total_cases * MANUAL_MINUTES_PER_TICKET
ai_total = auto_count * AI_MINUTES_PER_TICKET + review_count * REVIEW_MINUTES_PER_TICKET
time_saved = manual_total - ai_total
time_saved_pct = time_saved / manual_total if manual_total else 0

e1, e2, e3, e4 = st.columns(4)
e1.metric("Manual Process", f"{manual_total:.0f} min",
          help=f"{total_cases} cases x {MANUAL_MINUTES_PER_TICKET} min/case (industry benchmark)")
e2.metric("AI-Assisted Process", f"{ai_total:.0f} min",
          help=f"{auto_count} auto x {AI_MINUTES_PER_TICKET} min + {review_count} review x {REVIEW_MINUTES_PER_TICKET} min")
e3.metric("Time Saved", f"{time_saved:.0f} min",
          delta=f"{time_saved_pct:.0%} reduction")
ai_minutes_per_case = ai_total / total_cases if total_cases else 0
projected_savings_hrs = 10000 * (MANUAL_MINUTES_PER_TICKET - ai_minutes_per_case) / 60
e4.metric("Monthly Projection (10k cases)", f"{projected_savings_hrs:.0f} hrs saved",
          help=f"10,000 cases × ({MANUAL_MINUTES_PER_TICKET} - {ai_minutes_per_case:.1f}) min/case ÷ 60")

st.markdown("---")

# ---------------------------------------------------------------------------
# Key Insight Callout
# ---------------------------------------------------------------------------

st.header("Key Insight for Leadership")
st.markdown(f"""
> **At current automation rate ({automation_rate:.0%})**, the system can process
> **{auto_count} of {total_cases} cases** without human intervention.
> Each auto-routed case saves ~{MANUAL_MINUTES_PER_TICKET - AI_MINUTES_PER_TICKET:.0f} minutes of analyst time.
>
> **Top action items:**
> 1. Investigate top churn drivers — root causes driving the most customer loss
> 2. Review VIP cases flagged as high-risk — highest-value intervention targets
> 3. Address priority/risk misalignments — triage process may need calibration
>
> *All insights are auditable: every extraction includes evidence quotes from source text,
> and every routing decision has machine-readable reason codes.*
""")

st.caption("Data provenance: Results reflect current pipeline run. Mock data shows system structure; real provider data shows model quality.")
