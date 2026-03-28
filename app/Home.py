"""
Forward-Deployed AI Simulation — Home
AI-Augmented Ops Workflow Intelligence
"""
import streamlit as st

st.set_page_config(
    page_title="Forward-Deployed AI Simulation",
    page_icon="🔍",
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
    """)

with col2:
    st.subheader("Navigation")
    st.markdown("""
    1. **Problem Scoping** — Problem definition, AI suitability matrix, success criteria
    2. **Prototype Lab** — Run structuring on case bundles, inspect outputs
    3. **Reliability & Review** — Confidence gates, review queue, audit trails
    4. **Abstraction Layer** — Reusable modules, cross-industry transfer, roadmap
    """)

st.markdown("---")
st.caption("Phase 0 — Project brief locked. System > Model. Trust > Speed.")
