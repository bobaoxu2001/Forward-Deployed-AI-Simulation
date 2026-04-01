"""Page 8 — Human Feedback Loop: reviewers correct AI outputs, building a feedback dataset.

This page demonstrates the 'iterate to make sure this product is valuable to the end user'
principle. Every correction is saved to feedback.jsonl and used to measure human-AI agreement.
"""
import sys
import json
import sqlite3
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from pipeline.loaders import load_all_cases
from pipeline.normalize import normalize_case
from pipeline.feedback import (
    save_feedback,
    save_approval,
    load_all_feedback,
    compute_agreement_stats,
)
from pipeline.storage import deserialize_extraction

st.set_page_config(page_title="Human Feedback Loop", layout="wide")

DB_PATH = Path("data/processed/results.db")
CASES_DIR = Path("data/cases")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

if not DB_PATH.exists():
    st.warning("No pipeline results yet. Run `PYTHONPATH=. python scripts/run_pipeline.py --mock` first.")
    st.stop()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
extractions = {
    dict(r)["case_id"]: dict(r)
    for r in conn.execute("SELECT * FROM extractions").fetchall()
}
case_rows = {
    dict(r)["case_id"]: dict(r)
    for r in conn.execute("SELECT * FROM cases").fetchall()
}
conn.close()

cases_map = {}
if CASES_DIR.exists():
    for c in load_all_cases(CASES_DIR):
        cases_map[c.case_id] = c

if not extractions:
    st.info("No extractions in database.")
    st.stop()

# ---------------------------------------------------------------------------
# Page layout: tabs for Review and Analytics
# ---------------------------------------------------------------------------

st.title("Human Feedback Loop")
st.markdown(
    "Review AI extractions, correct errors, and approve good outputs. "
    "Every action builds a feedback dataset that measures human-AI alignment "
    "and informs prompt iteration."
)

tab_review, tab_analytics = st.tabs(["Review Cases", "Agreement Analytics"])

# ===========================================================================
# TAB 1: Review Cases
# ===========================================================================

with tab_review:
    st.markdown("---")

    # Case selector — prioritize review-routed cases
    review_cases = [cid for cid, ext in extractions.items() if ext.get("gate_route") == "review"]
    auto_cases = [cid for cid, ext in extractions.items() if ext.get("gate_route") == "auto"]

    # Check which cases already have feedback
    existing_feedback = load_all_feedback()
    reviewed_ids = {f["case_id"] for f in existing_feedback}

    case_options = []
    for cid in review_cases:
        tag = "reviewed" if cid in reviewed_ids else "needs review"
        case_options.append(f"{cid} [REVIEW] [{tag}]")
    for cid in auto_cases:
        tag = "reviewed" if cid in reviewed_ids else "auto-routed"
        case_options.append(f"{cid} [AUTO] [{tag}]")

    if not case_options:
        st.info("No cases to review.")
        st.stop()

    selected_option = st.selectbox("Select case to review", case_options)
    selected_id = selected_option.split(" ")[0]

    ext = extractions[selected_id]
    case_meta = case_rows.get(selected_id, {})
    case_bundle = cases_map.get(selected_id)

    ext = deserialize_extraction(ext)

    # --- Two columns: Source Text | AI Output + Correction ---
    col_source, col_review = st.columns([1, 1])

    with col_source:
        st.subheader("Source Text")
        ticket_text = case_meta.get("ticket_text", "")
        if case_bundle:
            ticket_text = case_bundle.ticket_text
        st.text_area("Raw input", ticket_text, height=250, disabled=True, label_visibility="collapsed")

        if case_bundle and case_bundle.conversation_snippet:
            with st.expander("Conversation snippet"):
                st.text(case_bundle.conversation_snippet)

        st.markdown("**Metadata**")
        st.markdown(
            f"Language: `{case_meta.get('language', '?')}` · "
            f"Priority: `{case_meta.get('priority', '?')}` · "
            f"VIP: `{case_meta.get('vip_tier', '?')}` · "
            f"Source: `{case_meta.get('source_dataset', '?')}`"
        )

        # Gate decision
        gate_route = ext.get("gate_route", "?")
        reason_codes = ext.get("review_reason_codes", [])
        if gate_route == "review":
            st.error(f"Gate: **REVIEW** — {', '.join(reason_codes) if reason_codes else 'unknown reason'}")
        else:
            st.success("Gate: **AUTO** — all checks passed")

    with col_review:
        st.subheader("AI Output → Your Correction")
        st.caption("Modify any field below. Leave unchanged if the AI got it right.")

        # Use a form to batch the corrections
        with st.form(key=f"review_form_{selected_id}"):
            ROOT_CAUSE_OPTIONS = [
                "billing", "network", "account", "product", "service",
                "security_breach", "outage", "vip_churn", "data_loss", "other", "unknown"
            ]
            RISK_OPTIONS = ["low", "medium", "high", "critical"]

            ai_rc_l1 = ext.get("root_cause_l1", "unknown")
            ai_rc_l2 = ext.get("root_cause_l2", "")
            ai_risk = ext.get("risk_level", "low")
            ai_sentiment = ext.get("sentiment_score", 0.0)
            ai_confidence = ext.get("confidence", 0.0)
            ai_churn = ext.get("churn_risk", 0.0)
            ai_review_req = bool(ext.get("review_required", False))

            # Root cause
            rc_l1_idx = ROOT_CAUSE_OPTIONS.index(ai_rc_l1) if ai_rc_l1 in ROOT_CAUSE_OPTIONS else 0
            corrected_rc_l1 = st.selectbox(
                f"Root Cause L1 (AI: `{ai_rc_l1}`)",
                ROOT_CAUSE_OPTIONS, index=rc_l1_idx
            )
            corrected_rc_l2 = st.text_input(
                f"Root Cause L2 (AI: `{ai_rc_l2}`)",
                value=ai_rc_l2
            )

            # Risk level
            risk_idx = RISK_OPTIONS.index(ai_risk) if ai_risk in RISK_OPTIONS else 0
            corrected_risk = st.selectbox(
                f"Risk Level (AI: `{ai_risk}`)",
                RISK_OPTIONS, index=risk_idx
            )

            # Sentiment
            corrected_sentiment = st.slider(
                f"Sentiment Score (AI: `{ai_sentiment:.2f}`)",
                -1.0, 1.0, float(ai_sentiment), step=0.1
            )

            # Confidence
            corrected_confidence = st.slider(
                f"Confidence (AI: `{ai_confidence:.2f}`)",
                0.0, 1.0, float(ai_confidence), step=0.05
            )

            # Churn risk
            corrected_churn = st.slider(
                f"Churn Risk (AI: `{ai_churn:.2f}`)",
                0.0, 1.0, float(ai_churn), step=0.05
            )

            # Review required
            corrected_review_req = st.checkbox(
                f"Review Required (AI: `{ai_review_req}`)",
                value=ai_review_req
            )

            # Reviewer notes
            reviewer_notes = st.text_area("Reviewer Notes", "", height=80)

            # Submit buttons
            col_approve, col_correct = st.columns(2)
            with col_approve:
                btn_approve = st.form_submit_button("Approve AI Output", type="secondary")
            with col_correct:
                btn_correct = st.form_submit_button("Submit Corrections", type="primary")

        # Handle form submission
        if btn_approve:
            entry = save_approval(selected_id, ext, reviewer_notes)
            st.success(f"Approved {selected_id}. Agreement rate: 100%")
            st.json(entry)

        if btn_correct:
            # Compute which fields changed
            corrected_fields = {}
            if corrected_rc_l1 != ai_rc_l1:
                corrected_fields["root_cause_l1"] = corrected_rc_l1
            if corrected_rc_l2 != ai_rc_l2:
                corrected_fields["root_cause_l2"] = corrected_rc_l2
            if corrected_risk != ai_risk:
                corrected_fields["risk_level"] = corrected_risk
            if abs(corrected_sentiment - ai_sentiment) > 0.05:
                corrected_fields["sentiment_score"] = corrected_sentiment
            if abs(corrected_confidence - ai_confidence) > 0.025:
                corrected_fields["confidence"] = corrected_confidence
            if abs(corrected_churn - ai_churn) > 0.025:
                corrected_fields["churn_risk"] = corrected_churn
            if corrected_review_req != ai_review_req:
                corrected_fields["review_required"] = corrected_review_req

            if not corrected_fields:
                st.info("No fields changed — this is equivalent to an approval.")
                entry = save_approval(selected_id, ext, reviewer_notes)
                st.success(f"Recorded as approval for {selected_id}.")
            else:
                entry = save_feedback(selected_id, ext, corrected_fields, reviewer_notes)
                st.success(
                    f"Saved corrections for {selected_id}. "
                    f"Fields corrected: {', '.join(corrected_fields.keys())}. "
                    f"Agreement: {entry['agreement']['agreement_rate']:.0%}"
                )
                st.json(entry)


# ===========================================================================
# TAB 2: Agreement Analytics
# ===========================================================================

with tab_analytics:
    st.markdown("---")

    all_feedback = load_all_feedback()

    if not all_feedback:
        st.info(
            "No feedback recorded yet. Use the **Review Cases** tab to approve or correct "
            "AI extractions. Each action builds the feedback dataset."
        )

        st.markdown("---")
        st.header("What This Page Will Show")
        st.markdown("""
        Once reviewers start providing feedback, this page displays:

        - **Overall human-AI agreement rate** — % of fields where the reviewer agreed with AI
        - **Per-field agreement** — which extraction fields are most/least reliable
        - **Most corrected fields** — where the AI consistently gets it wrong
        - **Correction timeline** — how agreement changes over time (ideally improves with prompt iteration)
        - **Feedback log** — full audit trail of every review action

        This is the data that drives prompt iteration: if reviewers keep correcting `risk_level`,
        the prompt needs better risk assessment instructions.
        """)
        st.stop()

    # Compute stats
    stats = compute_agreement_stats(all_feedback)

    # --- KPI Row ---
    st.header("Human-AI Agreement")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Reviews", stats["total_reviews"])
    k2.metric("Approvals", stats["approvals"],
              help="Cases where the reviewer accepted AI output without changes")
    k3.metric("Corrections", stats["corrections"],
              help="Cases where the reviewer changed at least one field")
    k4.metric("Overall Agreement Rate", f"{stats['overall_agreement_rate']:.0%}",
              help="% of reviewed fields where human agreed with AI")

    # --- Per-field agreement ---
    st.markdown("---")
    st.header("Per-Field Agreement")
    st.caption("Which extraction fields are most reliable? Fields with low agreement need prompt attention.")

    if stats["per_field_agreement"]:
        field_df = pd.DataFrame([
            {"Field": field, "Agreement Rate": rate}
            for field, rate in sorted(stats["per_field_agreement"].items(), key=lambda x: x[1])
        ])
        st.bar_chart(field_df.set_index("Field")["Agreement Rate"])
        st.dataframe(field_df, hide_index=True, use_container_width=True)

    # --- Most corrected fields ---
    if stats["most_corrected_fields"]:
        st.markdown("---")
        st.header("Most Corrected Fields")
        st.caption("These fields are corrected most often — primary targets for prompt improvement")

        corrected_df = pd.DataFrame(
            stats["most_corrected_fields"],
            columns=["Field", "Correction Count"],
        )
        st.bar_chart(corrected_df.set_index("Field"))
        st.dataframe(corrected_df, hide_index=True, use_container_width=True)

    # --- Feedback timeline ---
    st.markdown("---")
    st.header("Review Timeline")

    timeline_data = []
    for entry in all_feedback:
        ts = entry.get("timestamp", 0)
        timeline_data.append({
            "Time": pd.Timestamp.fromtimestamp(ts),
            "Case": entry.get("case_id", "?"),
            "Action": entry.get("action", "?"),
            "Agreement": entry.get("agreement", {}).get("agreement_rate", 0),
        })

    if timeline_data:
        timeline_df = pd.DataFrame(timeline_data)
        st.line_chart(timeline_df.set_index("Time")["Agreement"])
        st.dataframe(timeline_df, hide_index=True, use_container_width=True)

    # --- Full feedback log ---
    st.markdown("---")
    st.header("Feedback Log")
    st.caption(f"Full audit trail — {len(all_feedback)} entries in `data/processed/feedback.jsonl`")

    log_rows = []
    for entry in all_feedback:
        corrected = entry.get("corrected", {})
        log_rows.append({
            "Timestamp": pd.Timestamp.fromtimestamp(entry.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M"),
            "Case ID": entry.get("case_id", "?"),
            "Action": entry.get("action", "?"),
            "Fields Corrected": ", ".join(corrected.keys()) if corrected else "—",
            "Agreement": f"{entry.get('agreement', {}).get('agreement_rate', 0):.0%}",
            "Notes": entry.get("reviewer_notes", "")[:80],
        })

    if log_rows:
        st.dataframe(pd.DataFrame(log_rows), hide_index=True, use_container_width=True)

    # --- Insight callout ---
    st.markdown("---")
    st.markdown(
        "**How this drives iteration:** Every correction is a training signal. "
        "If `root_cause_l1` agreement drops below 80%, the prompt's classification "
        "instructions need refinement. If `confidence` is consistently corrected downward, "
        "the model is overconfident and needs calibration rules. "
        "This feedback loop closes the gap between 'works in demo' and 'works in production'."
    )
