"""Page 6 — ROI Model: quantified business case for AI-assisted support operations.

This page answers the CFO question: "What does this save us?"
Interactive sliders let stakeholders model their own scale assumptions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import sqlite3

DB_PATH = Path("data/processed/results.db")

st.set_page_config(page_title="ROI Model", layout="wide")
st.title("ROI Model")
st.markdown(
    "Interactive cost-benefit analysis comparing manual support operations "
    "to AI-assisted extraction and routing. Adjust assumptions with the sliders below."
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Load actuals from pipeline (for grounding the model in real data)
# ---------------------------------------------------------------------------

actual_automation_rate = 0.5  # conservative default before data loads
actual_avg_handle_time = 30.0
actual_total_cases = 0
actual_review_rate = 0.5

if DB_PATH.exists():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    exts = [dict(r) for r in conn.execute("SELECT * FROM extractions").fetchall()]
    cases = [dict(r) for r in conn.execute("SELECT * FROM cases").fetchall()]
    conn.close()

    if exts:
        actual_total_cases = len(exts)
        auto_count = sum(1 for e in exts if e.get("gate_route") == "auto")
        actual_automation_rate = auto_count / len(exts)
        actual_review_rate = 1 - actual_automation_rate

    if cases:
        handle_times = [c["handle_time_minutes"] for c in cases if c.get("handle_time_minutes")]
        if handle_times:
            actual_avg_handle_time = sum(handle_times) / len(handle_times)

# ---------------------------------------------------------------------------
# Sidebar: Assumptions (interactive)
# ---------------------------------------------------------------------------

st.sidebar.header("Model Assumptions")
st.sidebar.caption("Adjust these to match your organization's scale")

monthly_volume = st.sidebar.slider(
    "Monthly ticket volume", 1000, 100000, 10000, step=1000,
    help="Total support tickets per month"
)
analyst_hourly_cost = st.sidebar.slider(
    "Analyst cost ($/hour)", 15, 80, 35,
    help="Fully loaded cost per support analyst hour"
)
manual_minutes = st.sidebar.slider(
    "Manual processing time (min/ticket)", 5, 30, 15,
    help="Time to manually read, classify, tag, route, and document one ticket"
)
ai_auto_minutes = st.sidebar.slider(
    "AI auto-route time (min/ticket)", 0.1, 3.0, 0.5, step=0.1,
    help="Time for AI extraction + auto-routing (no human touch)"
)
ai_review_minutes = st.sidebar.slider(
    "AI-assisted review time (min/ticket)", 2, 15, 5,
    help="Time for human review with AI pre-analysis (vs. starting from scratch)"
)
api_cost_per_case = st.sidebar.slider(
    "API cost per extraction ($)", 0.001, 0.10, 0.01, step=0.001, format="%.3f",
    help="Claude API cost per structured extraction call"
)
automation_rate = st.sidebar.slider(
    "Automation rate (%)", 0, 100, int(actual_automation_rate * 100),
    help=f"Pipeline actual: {actual_automation_rate:.0%}. Higher = more cases auto-routed"
) / 100

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Pipeline actuals: {actual_total_cases} cases processed, "
    f"{actual_automation_rate:.0%} auto-routed, "
    f"{actual_avg_handle_time:.0f} min avg handle time"
)

# ---------------------------------------------------------------------------
# Cost Calculations
# ---------------------------------------------------------------------------

# Manual baseline
manual_hours = monthly_volume * manual_minutes / 60
manual_cost = manual_hours * analyst_hourly_cost

# AI-assisted
auto_cases = int(monthly_volume * automation_rate)
review_cases = monthly_volume - auto_cases
ai_labor_hours = (auto_cases * ai_auto_minutes + review_cases * ai_review_minutes) / 60
ai_labor_cost = ai_labor_hours * analyst_hourly_cost
ai_api_cost = monthly_volume * api_cost_per_case
ai_infra_cost = 500  # fixed monthly: hosting, monitoring, logging
ai_total_cost = ai_labor_cost + ai_api_cost + ai_infra_cost

# Savings
monthly_savings = manual_cost - ai_total_cost
annual_savings = monthly_savings * 12
roi_pct = (monthly_savings / ai_total_cost * 100) if ai_total_cost > 0 else 0
hours_saved = manual_hours - ai_labor_hours

# ---------------------------------------------------------------------------
# Display: Side-by-side comparison
# ---------------------------------------------------------------------------

st.header("Monthly Cost Comparison")

col_manual, col_ai = st.columns(2)

with col_manual:
    st.subheader("Manual Process")
    st.metric("Labor Hours", f"{manual_hours:,.0f} hrs")
    st.metric("Labor Cost", f"${manual_cost:,.0f}")
    st.metric("API Cost", "$0")
    st.metric("Infrastructure", "$0")
    st.markdown("---")
    st.metric("**Total Monthly Cost**", f"${manual_cost:,.0f}")

with col_ai:
    st.subheader("AI-Assisted Process")
    st.metric("Labor Hours", f"{ai_labor_hours:,.0f} hrs",
              delta=f"-{manual_hours - ai_labor_hours:,.0f} hrs", delta_color="inverse")
    st.metric("Labor Cost", f"${ai_labor_cost:,.0f}",
              delta=f"-${manual_cost - ai_labor_cost:,.0f}", delta_color="inverse")
    st.metric("API Cost", f"${ai_api_cost:,.0f}")
    st.metric("Infrastructure", f"${ai_infra_cost:,.0f}")
    st.markdown("---")
    st.metric("**Total Monthly Cost**", f"${ai_total_cost:,.0f}",
              delta=f"-${monthly_savings:,.0f}", delta_color="inverse")

# ---------------------------------------------------------------------------
# Savings Summary
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Savings Summary")

s1, s2, s3, s4 = st.columns(4)
s1.metric("Monthly Savings", f"${monthly_savings:,.0f}")
s2.metric("Annual Savings", f"${annual_savings:,.0f}")
s3.metric("ROI", f"{roi_pct:,.0f}%",
          help="(Monthly savings / AI total cost) × 100")
s4.metric("Hours Freed / Month", f"{hours_saved:,.0f} hrs",
          help="Analyst hours redirected to higher-value work")

# ---------------------------------------------------------------------------
# Break-even analysis
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Break-Even Analysis")

# At what automation rate does AI become cost-neutral?
st.markdown("**How does savings change with automation rate?**")

breakeven_data = []
for rate in range(0, 101, 5):
    r = rate / 100
    auto_c = int(monthly_volume * r)
    review_c = monthly_volume - auto_c
    labor_h = (auto_c * ai_auto_minutes + review_c * ai_review_minutes) / 60
    labor_c = labor_h * analyst_hourly_cost
    total_c = labor_c + ai_api_cost + ai_infra_cost
    saving = manual_cost - total_c
    breakeven_data.append({
        "Automation Rate": f"{rate}%",
        "rate_num": rate,
        "Monthly Savings ($)": saving,
    })

be_df = pd.DataFrame(breakeven_data)
st.line_chart(be_df.set_index("rate_num")["Monthly Savings ($)"])

# Find break-even point
breakeven_row = next((d for d in breakeven_data if d["Monthly Savings ($)"] >= 0), None)
if breakeven_row:
    st.success(
        f"Break-even at **{breakeven_row['Automation Rate']}** automation rate. "
        f"Current pipeline achieves **{automation_rate:.0%}**."
    )
else:
    st.warning("AI-assisted process is more expensive at all automation rates with current assumptions.")

# ---------------------------------------------------------------------------
# Scale projection table
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Scale Projections")
st.caption("How savings scale with ticket volume (holding other assumptions constant)")

scale_data = []
for vol in [1000, 5000, 10000, 25000, 50000, 100000]:
    m_cost = vol * manual_minutes / 60 * analyst_hourly_cost
    a_auto = int(vol * automation_rate)
    a_rev = vol - a_auto
    a_labor = (a_auto * ai_auto_minutes + a_rev * ai_review_minutes) / 60 * analyst_hourly_cost
    a_api = vol * api_cost_per_case
    a_total = a_labor + a_api + ai_infra_cost
    scale_data.append({
        "Monthly Volume": f"{vol:,}",
        "Manual Cost": f"${m_cost:,.0f}",
        "AI Cost": f"${a_total:,.0f}",
        "Monthly Savings": f"${m_cost - a_total:,.0f}",
        "Annual Savings": f"${(m_cost - a_total) * 12:,.0f}",
        "FTEs Freed": f"{(vol * manual_minutes / 60 - (a_auto * ai_auto_minutes + a_rev * ai_review_minutes) / 60) / 160:.1f}",
    })

scale_df = pd.DataFrame(scale_data)
st.dataframe(scale_df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Qualitative benefits
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Beyond Cost: Qualitative Benefits")

q1, q2, q3 = st.columns(3)

with q1:
    st.markdown("**Consistency**")
    st.markdown(
        "Manual classification varies 20-40% across analysts (industry benchmark). "
        "AI extraction applies the same schema to every case. "
        "Remaining variance is in the data, not the tagger."
    )

with q2:
    st.markdown("**Speed to Insight**")
    st.markdown(
        "Manual: monthly retrospective reports, weeks-old data. "
        "AI-assisted: real-time dashboard with structured data available "
        "within seconds of ticket ingestion."
    )

with q3:
    st.markdown("**Auditability**")
    st.markdown(
        "Every extraction includes evidence quotes from source text. "
        "Every routing decision has machine-readable reason codes. "
        "Every pipeline run is logged to JSONL trace files. "
        "Compliance teams can audit any decision."
    )

st.markdown("---")
st.caption(
    "Assumptions are adjustable via the sidebar. "
    "API costs based on Claude Sonnet pricing. "
    "FTE calculation assumes 160 working hours/month."
)
