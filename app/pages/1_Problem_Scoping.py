"""Problem Scoping — Problem definition, AI suitability, success criteria."""
import streamlit as st

st.set_page_config(page_title="Problem Scoping", layout="wide")
st.title("Problem Scoping")

st.header("Problem Statement")
st.markdown("""
Enterprise support teams have messy multilingual ticket/email/chat data and poor
visibility into churn drivers and operational risk. Manual classification is
inconsistent, retrospectives are anecdotal, and metrics lag reality by weeks.
""")

st.header("AI Suitability Matrix")

matrix_data = {
    "Task": [
        "Text cleanup & normalization",
        "Root cause / intent classification",
        "Sentiment / urgency / risk extraction",
        "Actionable recommendation generation",
        "Auto-reply to customers / SLA promises",
        "Executive insight: VIP churn drivers, Top-N risks",
    ],
    "AI Suitability": ["High", "High", "Medium", "Medium", "Low (blocked)", "High (conditional)"],
    "Control Strategy": [
        "Rules + lightweight model validation",
        "Structured output + confidence + sampling audit",
        "Output signal + evidence paragraph; no auto-attribution",
        "Must cite evidence; high-risk = mandatory review",
        "Prohibited; draft-only + review workflow",
        "Must show coverage rate, missing rate, uncertainty",
    ],
}
st.table(matrix_data)

st.header("Success Criteria")
st.markdown("""
| Metric | Target |
|---|---|
| Schema pass rate | >= 98% |
| Evidence coverage | >= 90% |
| Review routing precision | >= 0.8 |
| Review routing recall | >= 0.9 |
| Unsupported claim rate | <= 2% |
| Recommendation usefulness | >= 3.5/5 |
""")
