"""Page 2 — Prototype Lab: inspect how one case flows through the full pipeline."""
import sys
import json
import os
import sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from pipeline.schemas import CaseBundle
from pipeline.loaders import load_all_cases
from pipeline.normalize import normalize_case
from pipeline.extract import extract_case, MockProvider, ClaudeProvider
from pipeline.validate import validate_extraction, check_evidence_present
from pipeline.gate import compute_gate_decision

st.set_page_config(page_title="Prototype Lab", layout="wide")
st.title("Prototype Lab")

st.markdown(
    "**Pipeline:** Raw Text → Normalization → LLM Extraction (JSON) "
    "→ Schema Validation → Evidence Check → Risk Gate → Output"
)

st.divider()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DB_PATH = Path("data/processed/results.db")


def _load_stored_extraction(case_id: str) -> dict | None:
    """Load extraction from SQLite if it exists."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM extractions WHERE case_id = ?", (case_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    # Deserialize JSON-encoded list fields
    for key in ("next_best_actions", "evidence_quotes", "gate_reasons", "review_reason_codes"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _load_trace_metadata(case_id: str) -> dict | None:
    """Load most recent trace log for a case (tells us model name + latency)."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT model_name, prompt_version, latency_ms FROM trace_logs "
        "WHERE case_id = ? ORDER BY timestamp DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _is_real_result(trace: dict | None) -> bool:
    """Determine if a stored result came from a real model (not mock)."""
    if trace is None:
        return False
    return trace.get("model_name", "unknown") != "unknown" and trace.get("latency_ms", 0) > 0


def _has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# Load cases
# ---------------------------------------------------------------------------

cases_dir = Path("data/cases")
cases = []
if cases_dir.exists():
    cases = load_all_cases(cases_dir)

if not cases:
    st.warning("No cases found. Run `PYTHONPATH=. python scripts/build_cases.py` first.")
    st.stop()

# ---------------------------------------------------------------------------
# Case selector
# ---------------------------------------------------------------------------

case_ids = [c.case_id for c in cases]
selected_id = st.selectbox("Select a case", case_ids)
case = next(c for c in cases if c.case_id == selected_id)
case = normalize_case(case)

# Check for stored result
stored = _load_stored_extraction(case.case_id)
trace = _load_trace_metadata(case.case_id)
is_real = _is_real_result(trace)

# ---------------------------------------------------------------------------
# Extraction buttons
# ---------------------------------------------------------------------------

st.markdown("##### Run mode")
btn_cols = st.columns([1, 1, 1, 2])

with btn_cols[0]:
    load_disabled = stored is None
    load_label = "Load Existing Result"
    if stored is not None:
        load_label += " (real model)" if is_real else " (mock)"
    btn_load = st.button(load_label, disabled=load_disabled)

with btn_cols[1]:
    btn_mock = st.button("Run Mock Extraction")

with btn_cols[2]:
    has_key = _has_api_key()
    btn_real = st.button("Run Real Extraction", disabled=not has_key)
    if not has_key:
        st.caption("Set ANTHROPIC_API_KEY")

# Determine what to show
ext_dict = None
run_metadata = None

if btn_load and stored is not None:
    ext_dict = {
        "root_cause_l1": stored.get("root_cause_l1", ""),
        "root_cause_l2": stored.get("root_cause_l2", ""),
        "sentiment_score": stored.get("sentiment_score", 0.0),
        "risk_level": stored.get("risk_level", "low"),
        "review_required": bool(stored.get("review_required", False)),
        "next_best_actions": stored.get("next_best_actions", []),
        "evidence_quotes": stored.get("evidence_quotes", []),
        "confidence": stored.get("confidence", 0.0),
        "churn_risk": stored.get("churn_risk", 0.0),
        "sentiment_rationale": stored.get("sentiment_rationale", ""),
        "draft_notes": stored.get("draft_notes", ""),
    }
    run_metadata = {
        "model_name": trace.get("model_name", "unknown") if trace else "unknown",
        "prompt_version": trace.get("prompt_version", "?") if trace else "?",
        "latency_ms": trace.get("latency_ms", 0) if trace else 0,
        "source": "stored (real model)" if is_real else "stored (mock)",
    }
    st.session_state["ext_dict"] = ext_dict
    st.session_state["run_metadata"] = run_metadata

elif btn_mock:
    with st.spinner("Running mock extraction..."):
        output, meta = extract_case(case, provider=MockProvider())
    ext_dict = output.to_dict()
    run_metadata = {**meta, "source": "live (mock)"}
    st.session_state["ext_dict"] = ext_dict
    st.session_state["run_metadata"] = run_metadata

elif btn_real:
    with st.spinner("Calling Claude API..."):
        output, meta = extract_case(case, provider=ClaudeProvider())
    ext_dict = output.to_dict()
    run_metadata = {**meta, "source": "live (real model)"}
    st.session_state["ext_dict"] = ext_dict
    st.session_state["run_metadata"] = run_metadata

elif "ext_dict" in st.session_state:
    ext_dict = st.session_state["ext_dict"]
    run_metadata = st.session_state.get("run_metadata")


# ---------------------------------------------------------------------------
# Two-column layout: Raw Input | Extracted Output
# ---------------------------------------------------------------------------

st.divider()

col_left, col_right = st.columns(2)

# --- LEFT: Raw Input ---
with col_left:
    st.subheader("Raw Input")

    st.text_area(
        "Ticket text",
        case.ticket_text,
        height=180,
        disabled=True,
        label_visibility="collapsed",
    )

    if case.conversation_snippet:
        with st.expander("Conversation snippet", expanded=False):
            st.text(case.conversation_snippet)

    if case.email_thread:
        with st.expander("Email thread", expanded=False):
            st.text("\n---\n".join(case.email_thread))

    st.markdown("**Case metadata**")
    meta_df = pd.DataFrame([{
        "Language": case.language,
        "Priority": case.priority,
        "VIP Tier": case.vip_tier,
        "Handle Time": f"{case.handle_time_minutes} min",
        "Churned (30d)": "Yes" if case.churned_within_30d else "No",
        "Source": case.source_dataset,
    }])
    st.dataframe(meta_df, use_container_width=True, hide_index=True)

# --- RIGHT: Extracted Output ---
with col_right:
    st.subheader("Extracted Output")

    if ext_dict is None:
        st.info("Select a run mode above to view extraction results.")
    else:
        # Root cause
        rc_l1 = ext_dict.get("root_cause_l1", "—")
        rc_l2 = ext_dict.get("root_cause_l2", "—")
        st.markdown(f"**Root cause:** `{rc_l1}` / `{rc_l2}`")

        # Key metrics in a row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Sentiment", f"{ext_dict.get('sentiment_score', 0):.2f}")
        m2.metric("Risk", ext_dict.get("risk_level", "—"))
        m3.metric("Confidence", f"{ext_dict.get('confidence', 0):.2f}")
        m4.metric("Churn Risk", f"{ext_dict.get('churn_risk', 0):.2f}")

        # Next best actions
        actions = ext_dict.get("next_best_actions", [])
        if actions:
            st.markdown("**Next best actions**")
            for a in actions:
                st.markdown(f"- {a}")

        # Sentiment rationale
        rationale = ext_dict.get("sentiment_rationale", "")
        if rationale:
            st.markdown(f"**Sentiment rationale:** {rationale}")

        # Draft notes
        notes = ext_dict.get("draft_notes", "")
        if notes:
            with st.expander("Draft resolution notes"):
                st.write(notes)


# ---------------------------------------------------------------------------
# Validation & Gate section
# ---------------------------------------------------------------------------

if ext_dict is not None:
    st.divider()
    st.subheader("Validation & Gate Decision")

    v1, v2, v3 = st.columns(3)

    # Schema validation
    valid, errors = validate_extraction(ext_dict)
    with v1:
        st.markdown("**Schema validation**")
        if valid:
            st.success("PASS")
        else:
            st.error("FAIL")
            for e in errors:
                st.caption(f"• {e}")

    # Evidence presence
    ev_ok, ev_msg = check_evidence_present(ext_dict)
    with v2:
        st.markdown("**Evidence check**")
        if ev_ok:
            st.success(f"Present ({len(ext_dict.get('evidence_quotes', []))} quotes)")
        else:
            st.warning(ev_msg)

    # Gate decision
    gate = compute_gate_decision(ext_dict)
    with v3:
        st.markdown("**Gate decision**")
        if gate["route"] == "auto":
            st.success("AUTO — no review needed")
        else:
            st.error("REVIEW — human review required")

    # Reason codes (if review)
    if gate["review_reason_codes"]:
        st.markdown("**Reason codes triggering review:**")
        code_str = "  ".join([f"`{c}`" for c in gate["review_reason_codes"]])
        st.markdown(code_str)
        for reason in gate["reasons"]:
            st.caption(f"→ {reason}")


    # -------------------------------------------------------------------
    # Evidence section
    # -------------------------------------------------------------------

    st.divider()
    st.subheader("Evidence Grounding")
    st.caption(
        "Each quote below should be a verbatim substring of the raw input above. "
        "If a quote does not appear in the source text, it is hallucinated."
    )

    quotes = ext_dict.get("evidence_quotes", [])
    source_text = case.ticket_text + " " + case.conversation_snippet

    if not quotes:
        st.warning("No evidence quotes provided.")
    else:
        for i, q in enumerate(quotes, 1):
            q_clean = q.strip()
            # Check if quote is grounded in source
            is_grounded = q_clean.lower() in source_text.lower() if len(q_clean) > 5 else True

            col_num, col_quote, col_status = st.columns([0.5, 8, 1.5])
            with col_num:
                st.markdown(f"**{i}.**")
            with col_quote:
                st.markdown(f"*\"{q_clean}\"*")
            with col_status:
                if is_grounded:
                    st.markdown(":green[grounded]")
                else:
                    st.markdown(":red[not found in source]")


    # -------------------------------------------------------------------
    # Run metadata
    # -------------------------------------------------------------------

    st.divider()
    if run_metadata:
        source_label = run_metadata.get("source", "—")
        model = run_metadata.get("model_name", "—")
        prompt_v = run_metadata.get("prompt_version", "—")
        latency = run_metadata.get("latency_ms", 0)
        st.caption(
            f"**Run info:** {source_label} · model: {model} · "
            f"prompt: {prompt_v} · latency: {latency:.0f} ms"
        )
