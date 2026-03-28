"""Page 4 — Abstraction Layer: reusable modules, adjacent use cases, production roadmap."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Abstraction Layer", layout="wide")
st.title("Abstraction Layer")

st.markdown("""
This page extracts the reusable patterns from this deployment.
The goal is not a summary — it's a set of **modules with defined interfaces**
that can transfer to other enterprise workflows.
""")

# --- Reusable Modules ---
st.header("Reusable Modules")

modules = pd.DataFrame({
    "Module": [
        "Unstructured Ingestion",
        "Semantic Structuring Engine",
        "Risk & Review Router",
        "Observability & Audit Trail",
        "Evaluation Harness",
        "Insight Dashboard",
    ],
    "Input": [
        "Multi-source text + metadata",
        "Normalized case bundle + JSON schema",
        "Structured extraction + rule set",
        "Pipeline run data",
        "Predictions + gold labels",
        "Aggregated structured data",
    ],
    "Output": [
        "Normalized case bundle",
        "Structured extraction (root cause, sentiment, risk, reco, evidence)",
        "Gate decision + review queue assignment + reason codes",
        "Trace logs, evidence links, version records, JSONL audit trail",
        "Metrics, failure mode library, regression tests, markdown report",
        "Cross-tabs, top drivers, exportable briefings",
    ],
    "This Repo": [
        "pipeline/loaders.py + normalize.py",
        "pipeline/extract.py + schemas.py",
        "pipeline/gate.py",
        "pipeline/storage.py (trace_logs table + JSONL)",
        "eval/metrics.py + failure_modes.py + run_eval.py",
        "app/pages/ (Streamlit)",
    ],
})
st.dataframe(modules, use_container_width=True, hide_index=True)

# --- Module Interfaces ---
st.header("Key Interfaces")

st.subheader("1. Case Bundle (Input)")
st.code("""
CaseBundle:
    case_id: str
    ticket_text: str           # required
    email_thread: list[str]
    conversation_snippet: str
    vip_tier: str              # standard | vip | unknown
    priority: str              # low | medium | high | critical | unknown
    handle_time_minutes: float
    churned_within_30d: bool
""", language="python")

st.subheader("2. Extraction Output")
st.code("""
ExtractionOutput:
    root_cause_l1: str
    root_cause_l2: str
    sentiment_score: float     # -1.0 to 1.0
    risk_level: str            # low | medium | high | critical
    review_required: bool
    next_best_actions: list[str]
    evidence_quotes: list[str] # must quote source text
    confidence: float          # 0.0 to 1.0
    churn_risk: float          # 0.0 to 1.0
""", language="python")

st.subheader("3. Gate Decision")
st.code("""
GateDecision:
    route: str                 # auto | review
    reasons: list[str]         # human-readable
    review_reason_codes: list[str]  # machine-readable
""", language="python")

# --- Adjacent Use Cases ---
st.header("Adjacent Use Cases")

use_cases = pd.DataFrame({
    "Industry": ["Healthcare", "E-commerce", "Insurance", "Manufacturing"],
    "Input Data": [
        "Intake notes, triage forms, patient messages",
        "Post-sale tickets, returns, reviews",
        "Claims forms, adjuster notes, police reports",
        "Field repair logs, maintenance tickets",
    ],
    "Structuring Task": [
        "Risk stratification, triage routing, urgency classification",
        "Return root cause, experience defect aggregation",
        "Claim classification, missing info detection, fraud signals",
        "Fault attribution, spare parts prediction, escalation routing",
    ],
    "Key Difference": [
        "Stronger compliance (HIPAA), higher stakes",
        "Higher volume, lower risk per case",
        "Document-heavy, multi-step verification",
        "Domain-specific vocabulary, equipment codes",
    ],
})
st.dataframe(use_cases, use_container_width=True, hide_index=True)

# --- Production Roadmap ---
st.header("Production Roadmap")

st.markdown("""
This is a strategy, not an implementation plan.

| Phase | What | Why |
|-------|------|-----|
| **Auth & RBAC** | User roles: analyst, reviewer, admin | Control who sees what, who can approve |
| **Real data connectors** | Zendesk, ServiceNow, Salesforce adapters | Replace synthetic ingestion with live data |
| **Model evaluation loop** | A/B prompt versions, automated regression | Catch quality regressions before they reach users |
| **Feedback integration** | Reviewer edits flow back to eval set | Close the loop — human corrections improve the system |
| **Monitoring & alerting** | Schema fail rate, drift detection, latency SLOs | Know when the system degrades before users complain |
| **Compliance & audit** | Immutable trace logs, data retention policies | Enterprise requirement for regulated industries |
""")

# --- What we actually built ---
st.header("What We Actually Built & Measured")

db_path = Path("data/processed/results.db")
if db_path.exists():
    from pipeline.storage import get_all_extractions, get_review_queue
    all_ext = get_all_extractions()
    review_q = get_review_queue()

    c1, c2, c3 = st.columns(3)
    c1.metric("Cases Processed", len(all_ext))
    c2.metric("Auto-Routed", len(all_ext) - len(review_q))
    c3.metric("Sent to Review", len(review_q))

    # Run quick eval if we have data
    if all_ext:
        from eval.metrics import schema_pass_rate, evidence_coverage_rate
        ext_dicts = []
        for e in all_ext:
            import json
            d = dict(e)
            for field in ("next_best_actions", "evidence_quotes"):
                if d.get(field) and isinstance(d[field], str):
                    try:
                        d[field] = json.loads(d[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            ext_dicts.append(d)

        c4, c5 = st.columns(2)
        c4.metric("Schema Pass Rate", f"{schema_pass_rate(ext_dicts):.0%}")
        c5.metric("Evidence Coverage", f"{evidence_coverage_rate(ext_dicts):.0%}")
else:
    st.info("Run the pipeline to see measured results here.")
