"""Forward-Deployed AI Simulation — Home."""
import sys
import json
from pathlib import Path
from collections import Counter

# Add project root to path so pipeline/eval imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Forward-Deployed AI Simulation",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Hero section
# ---------------------------------------------------------------------------

st.title("Forward-Deployed AI Simulation")
st.markdown(
    "> *Turning noisy enterprise support data into structured operational insight, "
    "with reliability controls and reusable abstractions.*"
)

# Highlight reel — the 4 numbers that matter most
REAL_EVAL_PATH = Path("data/eval/batch_10_real_provider.md")
has_real_eval = REAL_EVAL_PATH.exists()

if has_real_eval:
    st.markdown("---")
    st.markdown("##### Validated with Claude Sonnet on 10 real cases")
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Schema Pass Rate", "100%", help="10/10 extractions pass JSON schema validation")
    h2.metric("Evidence Grounding", "97.3%", help="36 of 37 quotes are verbatim from source text")
    h3.metric("Human-AI Agreement", "90%", help="Field-level agreement across 15 reviewed cases")
    h4.metric("Prompt Iterations", "v1 → v2", help="Short-input confidence cap, zero code changes")

st.markdown("---")

# ---------------------------------------------------------------------------
# Two-column: what + where
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("What this system does")
    st.markdown("""
- **Structures** messy tickets, emails, and chats into root cause, sentiment, risk, and next actions
- **Gates** uncertain or high-risk outputs for human review
- **Audits** every decision with evidence quotes and trace logs
- **Evaluates** itself with measurable metrics and a failure mode library
- **Iterates** via human feedback loop and prompt A/B testing
    """)

with col2:
    st.subheader("Start here")
    st.page_link("pages/0_Engagement_Narrative.py", label="Engagement Narrative — the full story", icon="🎯")
    st.caption("Then explore the system:")
    st.markdown("""
1. **Problem Scoping** — AI suitability matrix, success criteria
2. **Prototype Lab** — Case-by-case pipeline inspection
3. **Reliability & Review** — Gate distribution, reason codes
4. **Abstraction Layer** — Reusable modules, production roadmap
5. **Executive Summary** — C-suite churn drivers, VIP risk
6. **ROI Model** — Interactive cost-benefit with sliders
7. **Data Quality** — Input EDA, noise signals, field completeness
8. **Human Feedback** — Correct AI outputs, track agreement rate
9. **Prompt A/B Testing** — Compare prompt versions quantitatively
    """)

# ---------------------------------------------------------------------------
# System status from DB
# ---------------------------------------------------------------------------

db_path = Path("data/processed/results.db")
if db_path.exists():
    from pipeline.storage import get_all_extractions, get_review_queue
    from pipeline.feedback import load_all_feedback, compute_agreement_stats

    st.markdown("---")
    st.subheader("Live System Status")

    all_ext = get_all_extractions()
    review_q = get_review_queue()
    feedback = load_all_feedback()
    agreement = compute_agreement_stats(feedback)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Extractions", len(all_ext))
    c2.metric("Auto-Routed", len(all_ext) - len(review_q))
    c3.metric("In Review Queue", len(review_q))
    c4.metric("Human Reviews", len(feedback))

    if all_ext:
        root_causes = Counter(e.get("root_cause_l1", "unknown") for e in all_ext)
        confidences = [e.get("confidence", 0) for e in all_ext if e.get("confidence")]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Root Cause Categories", len(root_causes))
        d2.metric("Avg Confidence", f"{avg_conf:.2f}")
        automation_rate = (len(all_ext) - len(review_q)) / len(all_ext)
        d3.metric("Automation Rate", f"{automation_rate:.0%}")
        if agreement["total_reviews"] > 0:
            d4.metric("Human-AI Agreement", f"{agreement['overall_agreement_rate']:.0%}")
        else:
            d4.metric("Human-AI Agreement", "—")
else:
    st.info("No pipeline results yet. Run `python scripts/run_pipeline.py --mock` to generate data.")

st.markdown("---")
st.caption("System > Model. Trust > Speed. Evaluation > Polish.")
