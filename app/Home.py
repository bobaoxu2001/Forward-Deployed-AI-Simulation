"""Forward-Deployed AI Simulation — Home."""
import sys
from pathlib import Path

# Add project root to path so pipeline/eval imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Forward-Deployed AI Simulation",
    layout="wide",
)

st.title("Forward-Deployed AI Simulation")
st.markdown(
    "> *Turning noisy enterprise support data into structured operational insight, "
    "with reliability controls and reusable abstractions.*"
)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("What this system does")
    st.markdown("""
- **Structures** messy tickets, emails, and chats into root cause, sentiment, risk, and next actions
- **Gates** uncertain or high-risk outputs for human review
- **Audits** every decision with evidence quotes and trace logs
- **Evaluates** itself with measurable metrics and a failure mode library
- **Abstracts** the solution into reusable modules for cross-industry transfer
    """)

with col2:
    st.subheader("Pages")
    st.markdown("""
1. **Problem Scoping** — Problem statement, AI suitability matrix, success criteria
2. **Prototype Lab** — Select a case, view raw input alongside extracted output
3. **Reliability & Review** — Review queue, reason codes, confidence distribution
4. **Abstraction Layer** — Reusable modules, adjacent use cases, production roadmap
    """)

# Quick stats from DB if available
db_path = Path("data/processed/results.db")
if db_path.exists():
    from pipeline.storage import get_all_extractions, get_review_queue
    st.markdown("---")
    st.subheader("System Status")
    all_ext = get_all_extractions()
    review_q = get_review_queue()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Extractions", len(all_ext))
    c2.metric("Auto-Routed", len(all_ext) - len(review_q))
    c3.metric("In Review Queue", len(review_q))
else:
    st.info("No pipeline results yet. Run `python scripts/run_pipeline.py --mock` to generate data.")

st.markdown("---")
st.caption("System > Model. Trust > Speed. Evaluation > Polish.")
