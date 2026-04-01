"""Page 7 — Data Quality Analysis: EDA of raw inputs before AI extraction.

This page demonstrates the forward-deployed mindset: before building models,
understand the data you're working with. Noise, missing fields, language mix,
and length distributions all affect extraction quality.
"""
import sys
import json
import sqlite3
import re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Quality Analysis", layout="wide")
st.title("Data Quality Analysis")
st.markdown(
    "Understanding input data quality before extraction. "
    "In a forward-deployed engagement, this analysis happens in week 1 — "
    "it determines prompt design, validation rules, and reliability thresholds."
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Load case bundles
# ---------------------------------------------------------------------------

CASES_DIR = Path("data/cases")
DB_PATH = Path("data/processed/results.db")

case_files = sorted(CASES_DIR.glob("*.json")) if CASES_DIR.exists() else []

if not case_files:
    st.warning("No case bundles found. Run `PYTHONPATH=. python scripts/build_cases.py` first.")
    st.stop()

cases = []
for f in case_files:
    with open(f) as fh:
        cases.append(json.load(fh))

df = pd.DataFrame(cases)

st.success(f"Loaded **{len(cases)}** case bundles from `data/cases/`")

# ---------------------------------------------------------------------------
# Section 1: Dataset Composition
# ---------------------------------------------------------------------------

st.header("Dataset Composition")
st.caption("Where does the data come from? What mix of sources feeds the pipeline?")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**By Source Dataset**")
    source_counts = df["source_dataset"].value_counts()
    st.bar_chart(source_counts)

with c2:
    st.markdown("**By Language**")
    lang_counts = df["language"].value_counts()
    st.bar_chart(lang_counts)

with c3:
    st.markdown("**By Priority**")
    priority_order = ["low", "medium", "high", "critical", "unknown"]
    if "priority" in df.columns:
        prio_counts = df["priority"].value_counts().reindex(
            [p for p in priority_order if p in df["priority"].values]
        )
        st.bar_chart(prio_counts)

# Summary table
st.markdown("---")
composition = pd.DataFrame({
    "Dimension": ["Sources", "Languages", "Priorities", "VIP Tiers"],
    "Unique Values": [
        df["source_dataset"].nunique(),
        df["language"].nunique(),
        df["priority"].nunique() if "priority" in df.columns else 0,
        df["vip_tier"].nunique() if "vip_tier" in df.columns else 0,
    ],
    "Distribution": [
        ", ".join(f"{k}: {v}" for k, v in df["source_dataset"].value_counts().items()),
        ", ".join(f"{k}: {v}" for k, v in df["language"].value_counts().items()),
        ", ".join(f"{k}: {v}" for k, v in df["priority"].value_counts().items()) if "priority" in df.columns else "—",
        ", ".join(f"{k}: {v}" for k, v in df["vip_tier"].value_counts().items()) if "vip_tier" in df.columns else "—",
    ],
})
st.dataframe(composition, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 2: Text Length Distribution
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Text Length Distribution")
st.caption(
    "Short inputs lack context for high-confidence extraction. "
    "This analysis directly informed our prompt v2 rule: "
    "cap confidence at 0.7 for inputs under 30 words."
)

df["text_length_chars"] = df["ticket_text"].str.len()
df["text_length_words"] = df["ticket_text"].str.split().str.len()

l1, l2 = st.columns(2)

with l1:
    st.markdown("**Character count distribution**")
    st.bar_chart(df["text_length_chars"].value_counts(bins=15).sort_index())
    st.caption(
        f"Min: {df['text_length_chars'].min()} · "
        f"Max: {df['text_length_chars'].max()} · "
        f"Median: {df['text_length_chars'].median():.0f} · "
        f"Mean: {df['text_length_chars'].mean():.0f}"
    )

with l2:
    st.markdown("**Word count distribution**")
    st.bar_chart(df["text_length_words"].value_counts(bins=15).sort_index())
    st.caption(
        f"Min: {df['text_length_words'].min()} · "
        f"Max: {df['text_length_words'].max()} · "
        f"Median: {df['text_length_words'].median():.0f} · "
        f"Mean: {df['text_length_words'].mean():.0f}"
    )

# Flag short inputs
short_threshold = 30
short_cases = df[df["text_length_words"] < short_threshold]
if len(short_cases) > 0:
    st.warning(
        f"**{len(short_cases)} cases ({len(short_cases)/len(df)*100:.0f}%)** "
        f"have fewer than {short_threshold} words. "
        f"These are high-risk for overconfident extraction. "
        f"Prompt v2 caps confidence at 0.7 for these cases."
    )
    with st.expander(f"View {len(short_cases)} short cases"):
        for _, row in short_cases.iterrows():
            st.markdown(
                f"**{row['case_id']}** ({row['text_length_words']} words) — "
                f"`{row['source_dataset']}`"
            )
            st.text(row["ticket_text"][:200])
            st.markdown("---")

# ---------------------------------------------------------------------------
# Section 3: Text Quality Signals
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Text Quality Signals")
st.caption("Noise patterns that affect extraction quality — detected programmatically")


def analyze_text_quality(text: str) -> dict:
    """Detect quality signals in a text input."""
    signals = {}
    # Encoding artifacts
    signals["encoding_artifacts"] = bool(re.search(r"[Ã¤Ã¶Ã¼Ã©]|\\u[0-9a-fA-F]{4}|&#\d+;", text))
    # Excessive whitespace
    signals["excessive_whitespace"] = bool(re.search(r"\n{3,}|\s{4,}", text))
    # Template placeholders
    signals["has_placeholders"] = bool(re.search(r"\{\{.*?\}\}|<name>|\[NAME\]|\[REDACTED\]", text))
    # All caps segments (shouting)
    signals["has_shouting"] = bool(re.search(r"\b[A-Z]{5,}\b", text))
    # Email headers
    signals["has_email_headers"] = bool(re.search(r"(From:|To:|Subject:|Date:)", text))
    # Contains non-ASCII (multilingual)
    signals["non_ascii"] = bool(re.search(r"[^\x00-\x7F]", text))
    # Very short
    signals["very_short"] = len(text.split()) < 30
    # Contains numbers / IDs
    signals["contains_ids"] = bool(re.search(r"(ticket|case|order|ref)[\s#:-]*\d+", text, re.I))
    return signals


quality_results = []
for _, row in df.iterrows():
    signals = analyze_text_quality(row["ticket_text"])
    signals["case_id"] = row["case_id"]
    quality_results.append(signals)

quality_df = pd.DataFrame(quality_results)

# Summary metrics
signal_cols = [c for c in quality_df.columns if c != "case_id"]
signal_summary = []
for col in signal_cols:
    count = quality_df[col].sum()
    signal_summary.append({
        "Signal": col.replace("_", " ").title(),
        "Cases Affected": count,
        "% of Dataset": f"{count / len(quality_df) * 100:.0f}%",
    })

signal_df = pd.DataFrame(signal_summary).sort_values("Cases Affected", ascending=False)
st.dataframe(signal_df, hide_index=True, use_container_width=True)

# Visual breakdown
st.markdown("**Signal frequency**")
chart_data = pd.DataFrame({
    row["Signal"]: [row["Cases Affected"]] for _, row in signal_df.iterrows()
})
st.bar_chart(signal_df.set_index("Signal")["Cases Affected"])

# ---------------------------------------------------------------------------
# Section 4: Multilingual Analysis
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Multilingual Analysis")
st.caption("Non-English inputs require special handling — the extraction must preserve source language evidence")

lang_groups = df.groupby("language")

for lang, group in lang_groups:
    with st.expander(f"**{lang.upper()}** — {len(group)} cases"):
        st.markdown(f"**Avg word count:** {group['text_length_words'].mean():.0f}")
        st.markdown(f"**Priority mix:** {dict(group['priority'].value_counts())}")
        st.markdown(f"**Source datasets:** {dict(group['source_dataset'].value_counts())}")

        # Show example
        example = group.iloc[0]
        st.markdown("**Example:**")
        st.text(example["ticket_text"][:300])

# ---------------------------------------------------------------------------
# Section 5: Field Completeness
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Field Completeness")
st.caption("Missing or empty fields in case bundles — gaps the extraction must handle gracefully")

completeness = []
for col in ["ticket_text", "email_thread", "conversation_snippet", "vip_tier", "priority",
            "handle_time_minutes", "source_dataset", "language"]:
    if col not in df.columns:
        continue

    if col == "email_thread":
        filled = df[col].apply(lambda x: len(x) > 0 if isinstance(x, list) else bool(x)).sum()
    elif col == "handle_time_minutes":
        filled = df[col].apply(lambda x: x > 0 if x else False).sum()
    else:
        filled = df[col].apply(lambda x: bool(x) and x not in ("", "unknown")).sum()

    completeness.append({
        "Field": col,
        "Filled": filled,
        "Missing/Default": len(df) - filled,
        "Completeness": f"{filled / len(df) * 100:.0f}%",
    })

comp_df = pd.DataFrame(completeness)
st.dataframe(comp_df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 6: Churn Label Distribution
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Label Distribution")
st.caption("Synthetic labels (churn, VIP) — understanding class balance for evaluation")

l1, l2 = st.columns(2)

with l1:
    st.markdown("**Churn within 30 days**")
    churn_counts = df["churned_within_30d"].value_counts()
    churn_display = pd.DataFrame({
        "Status": ["Retained", "Churned"],
        "Count": [
            churn_counts.get(False, 0) + churn_counts.get(0, 0),
            churn_counts.get(True, 0) + churn_counts.get(1, 0),
        ],
    })
    st.bar_chart(churn_display.set_index("Status"))
    churn_total = churn_display["Count"].sum()
    churned = churn_display[churn_display["Status"] == "Churned"]["Count"].values[0]
    st.caption(f"Churn rate: {churned/churn_total*100:.0f}% — {'balanced enough for evaluation' if 0.15 < churned/churn_total < 0.5 else 'may need rebalancing'}")

with l2:
    st.markdown("**VIP Tier**")
    if "vip_tier" in df.columns:
        vip_counts = df["vip_tier"].value_counts()
        st.bar_chart(vip_counts)
    else:
        st.info("VIP tier not available.")

# ---------------------------------------------------------------------------
# Section 7: Data Quality Score
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Overall Data Quality Score")

# Compute a simple quality score
total_signals = sum(quality_df[c].sum() for c in signal_cols)
max_signals = len(quality_df) * len(signal_cols)
quality_score = 1 - (total_signals / max_signals)

q1, q2, q3 = st.columns(3)
q1.metric("Quality Score", f"{quality_score:.0%}",
          help="1 - (total noise signals / max possible signals). Higher = cleaner data.")
q2.metric("Total Noise Signals", f"{total_signals}",
          help=f"Across {len(quality_df)} cases × {len(signal_cols)} signal types")
q3.metric("Cases with No Issues", f"{len(quality_df[quality_df[signal_cols].sum(axis=1) == 0])}",
          help="Cases that triggered zero noise signals")

st.markdown("---")
st.markdown(
    "**Why this matters for forward-deployed AI:** "
    "Data quality analysis is not optional — it's the first deliverable in week 1. "
    "Noise patterns directly inform prompt engineering (e.g., the short-input confidence cap), "
    "validation rules (e.g., evidence grounding checks), and gate thresholds. "
    "A system that doesn't understand its own input data cannot be trusted to produce reliable output."
)
