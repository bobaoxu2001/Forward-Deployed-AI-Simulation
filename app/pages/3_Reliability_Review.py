"""Reliability & Review — Confidence gates, review queue, audit trails."""
import streamlit as st

st.set_page_config(page_title="Reliability & Review", layout="wide")
st.title("Reliability & Review")

st.markdown("""
### Risk Gate Logic
- **Low risk + high confidence** → auto-route to structured store
- **High risk OR low confidence** → human review queue
- **High-risk categories** (security breach, outage, VIP churn) → sampled review even at high confidence (10%)

### Audit Trail
Every output records:
- Evidence quotes linking each field to source text
- Validation results (schema pass/fail, constraint checks)
- Gate decision and reasoning
- Human review edits (if any) fed back to eval

### Failure Mode Tags
- Hallucination — no evidence for claim
- Omission — clear signal missed
- Overconfidence — high confidence, wrong answer
- Ambiguity — genuinely uncertain, needs more info
- Language/format drift — multilingual collapse
- Spurious correlation — confounders misread as causes
""")

st.warning("Review queue not yet connected. Complete Phase C to enable.")
