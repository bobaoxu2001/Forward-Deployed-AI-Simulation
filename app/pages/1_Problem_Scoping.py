"""Page 1 — Problem Scoping: problem statement, workflows, AI suitability, success criteria."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Problem Scoping", layout="wide")
st.title("Problem Scoping")

# --- Problem Statement ---
st.header("Problem Statement")
st.markdown("""
Enterprise support teams (telecom, contact centers) generate massive volumes of
unstructured text — tickets, emails, chats, resolution notes — that are multilingual,
noisy, and fragmented across systems.

**The result:** Management has no timely visibility into systemic risk drivers or
VIP churn causes. Manual classification is inconsistent, retrospectives are anecdotal,
and metrics lag reality by weeks.
""")

# --- Workflow Before/After ---
st.header("Workflow")
col_before, col_after = st.columns(2)

with col_before:
    st.subheader("Before (Manual)")
    st.markdown("""
```
Raw Tickets/Emails/Chats
    -> Frontline Agent Reads
    -> Manual Tagging & Routing
    -> Manual Investigation
    -> Resolution Notes (Free Text)
    -> Weekly/Monthly Reporting (Lagging)
    -> C-suite Decisions (Low Visibility)
```
    """)

with col_after:
    st.subheader("After (AI-Augmented)")
    st.markdown("""
```
Raw Tickets/Emails/Chats
    -> Ingestion & Normalization
    -> LLM Structuring (JSON Schema)
    -> Confidence / Risk Gate
        Low Risk  -> Auto-Route + Draft Reco
        High Risk -> Human Review Queue
    -> Structured Store (SQLite)
    -> Dashboard (Root cause x Churn x VIP)
    -> Audit Trail & Eval Harness
```
    """)

# --- AI Suitability Matrix ---
st.header("AI Suitability Matrix")
matrix = pd.DataFrame({
    "Task": [
        "Text cleanup & normalization",
        "Root cause / intent classification",
        "Sentiment / urgency / risk extraction",
        "Actionable recommendation generation",
        "Auto-reply to customers / SLA promises",
        "Executive insight: VIP churn drivers",
    ],
    "AI Suitability": [
        "High",
        "High",
        "Medium",
        "Medium",
        "Not Permitted",
        "High (conditional)",
    ],
    "Control Strategy": [
        "Rules + lightweight model validation",
        "Structured output + confidence + sampling audit",
        "Output signal + evidence paragraph; no auto-attribution",
        "Must cite evidence; high-risk = mandatory review",
        "BLOCKED: draft-only + human review workflow",
        "Must show coverage rate, missing rate, uncertainty",
    ],
})
st.dataframe(matrix, use_container_width=True, hide_index=True)

# --- Success Criteria ---
st.header("Success Criteria")
criteria = pd.DataFrame({
    "Metric": [
        "Schema pass rate",
        "Evidence coverage rate",
        "Unsupported claim rate",
        "Review routing precision",
        "Review routing recall",
        "Recommendation usefulness",
    ],
    "Target": [">= 98%", ">= 90%", "<= 2%", ">= 0.80", ">= 0.90", ">= 3.5/5"],
    "Why It Matters": [
        "Every output must be structurally valid",
        "Every claim must be backed by source text",
        "Recommendations without evidence erode trust",
        "Don't waste human reviewers on low-risk cases",
        "Don't miss cases that actually need review",
        "Suggestions must be actionable, not generic",
    ],
})
st.dataframe(criteria, use_container_width=True, hide_index=True)

# --- Non-goals ---
st.header("Explicit Non-Goals")
st.markdown("""
- No production auth or user accounts
- No real CRM/Zendesk/ServiceNow integration
- No customer-facing auto-send (AI never sends messages to customers)
- No online learning or continuous training
- No storing raw dataset files in repo
""")
