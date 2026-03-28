"""Page 2 — Prototype Lab: select a case, view raw input + extracted output + gate decision."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from pipeline.schemas import CaseBundle
from pipeline.loaders import load_all_cases
from pipeline.normalize import normalize_case
from pipeline.extract import extract_case, MockProvider
from pipeline.validate import validate_extraction, check_evidence_present
from pipeline.gate import compute_gate_decision

st.set_page_config(page_title="Prototype Lab", layout="wide")
st.title("Prototype Lab")

st.markdown("""
**Pipeline:** Raw Text → Normalization → LLM Structuring (JSON Schema) → Validation → Risk Gate → Output
""")

# --- Load cases ---
cases_dir = Path("data/cases")
cases = []
if cases_dir.exists():
    cases = load_all_cases(cases_dir)

if not cases:
    st.warning("No cases found. Run `python scripts/build_cases.py` first.")
    st.stop()

# --- Case selector ---
case_ids = [c.case_id for c in cases]
selected_id = st.selectbox("Select Case", case_ids)
case = next(c for c in cases if c.case_id == selected_id)
case = normalize_case(case)

# --- Layout: raw input | extracted output ---
col_input, col_output = st.columns(2)

with col_input:
    st.subheader("Raw Input")
    st.text_area("Ticket Text", case.ticket_text, height=150, disabled=True)
    if case.conversation_snippet:
        st.text_area("Conversation", case.conversation_snippet, height=100, disabled=True)
    if case.email_thread:
        st.text_area("Email Thread", "\n---\n".join(case.email_thread), height=100, disabled=True)

    st.markdown("**Metadata**")
    meta_df = pd.DataFrame([{
        "VIP Tier": case.vip_tier,
        "Priority": case.priority,
        "Handle Time": f"{case.handle_time_minutes} min",
        "Churned (30d)": case.churned_within_30d,
        "Language": case.language,
        "Source": case.source_dataset,
    }])
    st.dataframe(meta_df, use_container_width=True, hide_index=True)

with col_output:
    st.subheader("Extracted Output")

    # Run extraction with mock provider
    if st.button("Run Extraction", type="primary"):
        with st.spinner("Extracting..."):
            extraction, metadata = extract_case(case, provider=MockProvider())
            st.session_state["extraction"] = extraction
            st.session_state["metadata"] = metadata

    if "extraction" in st.session_state:
        ext = st.session_state["extraction"]
        meta = st.session_state["metadata"]
        ext_dict = ext.to_dict()

        # Structured output
        st.json(ext_dict)

        # Validation
        valid, errors = validate_extraction(ext_dict)
        has_evidence, ev_msg = check_evidence_present(ext_dict)

        st.markdown("**Validation**")
        if valid:
            st.success("Schema: PASS")
        else:
            st.error(f"Schema: FAIL — {errors}")

        if has_evidence:
            st.success(f"Evidence: {ev_msg}")
        else:
            st.warning(f"Evidence: {ev_msg}")

        # Gate decision
        gate = compute_gate_decision(ext_dict)
        st.markdown("**Risk Gate**")
        if gate["route"] == "auto":
            st.success("Route: AUTO")
        else:
            st.error(f"Route: REVIEW")
            for reason in gate["reasons"]:
                st.markdown(f"- {reason}")

        # Evidence quotes
        if ext.evidence_quotes:
            st.markdown("**Evidence Quotes**")
            for i, q in enumerate(ext.evidence_quotes, 1):
                st.markdown(f"{i}. _{q}_")

        # Run metadata
        st.markdown("**Run Metadata**")
        st.caption(f"Model: {meta.get('model_name', '?')} | "
                   f"Prompt: {meta.get('prompt_version', '?')} | "
                   f"Latency: {meta.get('latency_ms', 0):.0f}ms")
    else:
        st.info("Click 'Run Extraction' to process this case.")
