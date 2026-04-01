"""Page 9 — Prompt A/B Testing: compare prompt versions with quantified metrics.

Demonstrates continuous optimization capability — the kind of iteration that makes
a forward-deployed AI product valuable over time, not just at launch.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Prompt A/B Testing", layout="wide")
st.title("Prompt A/B Testing")
st.markdown(
    "Side-by-side comparison of prompt versions. Every prompt change is tested against "
    "the same cases with the same metrics — no guessing whether a change helped."
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Prompt Version Registry
# ---------------------------------------------------------------------------

# Each version records: the change, the hypothesis, and the measured results.
# In production, this would be stored in a database. Here we hardcode the
# actual results from our documented experiments.

PROMPT_VERSIONS = {
    "v1": {
        "label": "v1 — Baseline",
        "description": "Initial extraction prompt with structured JSON schema, evidence grounding rules, and ambiguity handling.",
        "change": "N/A (baseline)",
        "hypothesis": "N/A (baseline)",
        "prompt_diff": None,
        "eval_cases": 10,
        "model": "claude-sonnet-4-20250514",
        "metrics": {
            "Schema pass rate": {"value": 1.00, "target": 0.98, "pass": True},
            "Evidence coverage": {"value": 1.00, "target": 0.90, "pass": True},
            "Hallucinated quotes": {"value": 0.027, "target": 0.02, "pass": False},
            "Review-required rate": {"value": 0.80, "target": None, "pass": None},
            "Avg confidence": {"value": 0.82, "target": None, "pass": None},
            "Avg latency (ms)": {"value": 6341, "target": None, "pass": None},
        },
        "issues_found": [
            "Overconfidence on short inputs (2 of 4 short cases got 0.90 confidence)",
            "Metadata line quoted as evidence (1 of 37 quotes)",
            "Risk underestimation on termination/churn signals",
        ],
        "per_case_confidence": {
            "case-acaecb0d": {"words": 14, "confidence": 0.90},
            "case-f541aaa0": {"words": 8, "confidence": 0.90},
            "case-652870dc": {"words": 95, "confidence": 0.90},
            "case-ac7b0b06": {"words": 84, "confidence": 0.90},
            "case-2bd562d3": {"words": 7, "confidence": 0.60},
            "case-5f87257e": {"words": 11, "confidence": 0.60},
        },
    },
    "v2": {
        "label": "v2 — Short-Input Confidence Cap",
        "description": "Added one rule: 'If the case text is very short (under ~30 words), cap confidence at 0.7 — brief inputs lack context for high-certainty analysis.'",
        "change": "One prompt line added to RULES section",
        "hypothesis": "Short inputs (< 30 words) will get capped confidence without affecting long inputs.",
        "prompt_diff": (
            '+ - If the case text is very short (under ~30 words), cap confidence at 0.7 — '
            'brief inputs lack context for high-certainty analysis'
        ),
        "eval_cases": 10,
        "model": "claude-sonnet-4-20250514",
        "metrics": {
            "Schema pass rate": {"value": 1.00, "target": 0.98, "pass": True},
            "Evidence coverage": {"value": 1.00, "target": 0.90, "pass": True},
            "Hallucinated quotes": {"value": 0.027, "target": 0.02, "pass": False},
            "Review-required rate": {"value": 0.90, "target": None, "pass": None},
            "Avg confidence": {"value": 0.77, "target": None, "pass": None},
            "Avg latency (ms)": {"value": 6400, "target": None, "pass": None},
        },
        "issues_found": [
            "Hallucinated metadata quote still present (prompt clarification needed)",
            "Risk underestimation on termination/churn signals (separate issue from confidence)",
        ],
        "per_case_confidence": {
            "case-acaecb0d": {"words": 14, "confidence": 0.70},
            "case-f541aaa0": {"words": 8, "confidence": 0.60},
            "case-652870dc": {"words": 95, "confidence": 0.90},
            "case-ac7b0b06": {"words": 84, "confidence": 0.90},
            "case-2bd562d3": {"words": 7, "confidence": 0.60},
            "case-5f87257e": {"words": 11, "confidence": 0.60},
        },
    },
}

# Future prompt versions would be added here:
# "v3": { ... evidence boundary clarification ... }
# "v4": { ... churn signal boosting ... }

# ---------------------------------------------------------------------------
# Version selector
# ---------------------------------------------------------------------------

st.header("Select Versions to Compare")

versions = list(PROMPT_VERSIONS.keys())
col_a, col_b = st.columns(2)

with col_a:
    version_a = st.selectbox("Version A", versions, index=0)
with col_b:
    version_b = st.selectbox("Version B", versions, index=len(versions) - 1)

va = PROMPT_VERSIONS[version_a]
vb = PROMPT_VERSIONS[version_b]

# ---------------------------------------------------------------------------
# Section 1: Version Details
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Version Details")

d1, d2 = st.columns(2)

with d1:
    st.subheader(va["label"])
    st.markdown(f"**Description:** {va['description']}")
    st.markdown(f"**Model:** `{va['model']}`")
    st.markdown(f"**Eval cases:** {va['eval_cases']}")
    if va["prompt_diff"]:
        st.code(va["prompt_diff"], language="diff")

with d2:
    st.subheader(vb["label"])
    st.markdown(f"**Description:** {vb['description']}")
    st.markdown(f"**Change:** {vb['change']}")
    st.markdown(f"**Hypothesis:** {vb['hypothesis']}")
    st.markdown(f"**Model:** `{vb['model']}`")
    st.markdown(f"**Eval cases:** {vb['eval_cases']}")
    if vb["prompt_diff"]:
        st.code(vb["prompt_diff"], language="diff")

# ---------------------------------------------------------------------------
# Section 2: Metrics Comparison
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Metrics Comparison")

# Build comparison table
all_metrics = sorted(set(list(va["metrics"].keys()) + list(vb["metrics"].keys())))
comparison_rows = []

for metric in all_metrics:
    ma = va["metrics"].get(metric, {})
    mb = vb["metrics"].get(metric, {})

    val_a = ma.get("value", "—")
    val_b = mb.get("value", "—")
    target = ma.get("target") or mb.get("target")

    # Format values
    if isinstance(val_a, float) and val_a < 1:
        fmt_a = f"{val_a:.1%}" if metric != "Avg latency (ms)" else f"{val_a:,.0f}"
    else:
        fmt_a = f"{val_a:,.0f}" if isinstance(val_a, (int, float)) else str(val_a)

    if isinstance(val_b, float) and val_b < 1:
        fmt_b = f"{val_b:.1%}" if metric != "Avg latency (ms)" else f"{val_b:,.0f}"
    else:
        fmt_b = f"{val_b:,.0f}" if isinstance(val_b, (int, float)) else str(val_b)

    # Compute delta
    delta = ""
    if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
        diff = val_b - val_a
        if metric == "Avg latency (ms)":
            delta = f"{diff:+,.0f} ms"
        elif abs(diff) > 0.001:
            delta = f"{diff:+.1%}" if abs(val_a) < 10 else f"{diff:+,.0f}"

    # Determine if delta is improvement
    # Lower is better for: hallucinated quotes, latency
    # Higher is better for: schema pass rate, evidence coverage
    direction = ""
    if delta and isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
        diff = val_b - val_a
        lower_better = metric in ("Hallucinated quotes", "Avg latency (ms)")
        if abs(diff) > 0.001:
            is_better = (diff < 0) if lower_better else (diff > 0)
            direction = "better" if is_better else "worse" if abs(diff) > 0.001 else "same"

    comparison_rows.append({
        "Metric": metric,
        f"{version_a}": fmt_a,
        f"{version_b}": fmt_b,
        "Delta": delta,
        "Direction": direction,
        "Target": f"{target:.0%}" if isinstance(target, float) and target < 1 else (str(target) if target else "—"),
    })

comp_df = pd.DataFrame(comparison_rows)

# Style the dataframe
st.dataframe(comp_df, hide_index=True, use_container_width=True)

# Metrics as cards
st.markdown("### Key Deltas")
delta_cols = st.columns(len(all_metrics))
for i, row in enumerate(comparison_rows):
    with delta_cols[i % len(delta_cols)]:
        val_a_raw = va["metrics"].get(row["Metric"], {}).get("value", 0)
        val_b_raw = vb["metrics"].get(row["Metric"], {}).get("value", 0)
        if isinstance(val_a_raw, (int, float)) and isinstance(val_b_raw, (int, float)):
            if row["Metric"] == "Avg latency (ms)":
                st.metric(row["Metric"], f"{val_b_raw:,.0f}", delta=row["Delta"])
            elif val_b_raw < 1:
                st.metric(row["Metric"], f"{val_b_raw:.1%}", delta=row["Delta"])
            else:
                st.metric(row["Metric"], f"{val_b_raw}", delta=row["Delta"])

# ---------------------------------------------------------------------------
# Section 3: Per-Case Confidence Comparison
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Per-Case Confidence: v1 → v2")
st.caption("The specific cases that motivated the prompt change — did the fix work?")

case_ids = sorted(
    set(list(va.get("per_case_confidence", {}).keys()) + list(vb.get("per_case_confidence", {}).keys()))
)

case_comparison = []
for cid in case_ids:
    ca = va.get("per_case_confidence", {}).get(cid, {})
    cb = vb.get("per_case_confidence", {}).get(cid, {})
    words = ca.get("words") or cb.get("words", "?")
    conf_a = ca.get("confidence", "—")
    conf_b = cb.get("confidence", "—")

    delta = ""
    if isinstance(conf_a, (int, float)) and isinstance(conf_b, (int, float)):
        diff = conf_b - conf_a
        delta = f"{diff:+.2f}" if abs(diff) > 0.001 else "0.00"

    is_short = isinstance(words, int) and words < 30
    case_comparison.append({
        "Case ID": cid,
        "Words": words,
        "Short Input": "yes" if is_short else "no",
        f"Confidence ({version_a})": conf_a if isinstance(conf_a, str) else f"{conf_a:.2f}",
        f"Confidence ({version_b})": conf_b if isinstance(conf_b, str) else f"{conf_b:.2f}",
        "Delta": delta,
        "Fixed?": "YES" if is_short and isinstance(conf_b, (int, float)) and conf_b <= 0.7 else
                  ("n/a" if not is_short else "no"),
    })

case_df = pd.DataFrame(case_comparison)
st.dataframe(case_df, hide_index=True, use_container_width=True)

# Highlight results
short_cases = [c for c in case_comparison if c["Short Input"] == "yes"]
fixed_cases = [c for c in short_cases if c["Fixed?"] == "YES"]

if short_cases:
    st.success(
        f"**{len(fixed_cases)} of {len(short_cases)} short-input cases fixed** — "
        f"confidence capped at 0.7 or below. "
        f"Long inputs ({len(case_comparison) - len(short_cases)} cases) unaffected."
    )

# ---------------------------------------------------------------------------
# Section 4: Issues Resolved / Remaining
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Issues Tracking")

i1, i2 = st.columns(2)

with i1:
    st.subheader(f"Issues in {version_a}")
    for issue in va.get("issues_found", []):
        st.markdown(f"- {issue}")

with i2:
    st.subheader(f"Issues in {version_b}")
    for issue in vb.get("issues_found", []):
        st.markdown(f"- {issue}")

    resolved = set(va.get("issues_found", [])) - set(vb.get("issues_found", []))
    if resolved:
        st.markdown("**Resolved:**")
        for r in resolved:
            st.markdown(f"- ~~{r}~~")

# ---------------------------------------------------------------------------
# Section 5: Iteration Framework
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Prompt Iteration Framework")
st.caption("The systematic process used for every prompt change")

st.markdown("""
| Step | Action | Example (v1 → v2) |
|------|--------|--------------------|
| 1. **Observe** | Identify failure mode in eval data | 2 of 4 short inputs got 0.90 confidence |
| 2. **Hypothesize** | Root-cause the failure | Prompt says "if ambiguous, lower confidence" but short ≠ ambiguous |
| 3. **Change** | Minimal prompt edit (one rule) | Added: "If text < 30 words, cap confidence at 0.7" |
| 4. **Measure** | Re-run same cases, same metrics | Short-input confidence: 0.90 → 0.65 avg |
| 5. **Verify** | Check for regressions | Long-input confidence unchanged (0.90 → 0.90) |
| 6. **Document** | Record change, results, and remaining issues | This page |
""")

st.markdown("---")
st.header("Next Prompt Iterations (Planned)")

st.markdown("""
| Version | Change | Hypothesis | Status |
|---------|--------|------------|--------|
| **v3** | Clarify evidence boundary: "Do NOT quote metadata lines" | Eliminates metadata-as-evidence hallucination (1/37 quotes) | Planned |
| **v4** | Boost churn signal: "Termination/cancellation inquiries indicate high churn risk" | Catches risk underestimation on churn signals | Planned |
| **v5** | Add L2 taxonomy: controlled vocabulary for sub-categories | Improves cross-run consistency for root cause analysis | Planned |
""")

st.markdown("---")
st.caption(
    "Each prompt version is tested on the same 10-case diverse sample. "
    "Zero code changes between versions — only prompt text and version bump. "
    "This demonstrates that the system is designed for continuous improvement, "
    "not one-shot deployment."
)
