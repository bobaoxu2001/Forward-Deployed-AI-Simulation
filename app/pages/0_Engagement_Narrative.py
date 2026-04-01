"""Page 0 — Engagement Narrative: how a forward-deployed engagement actually works.

This page tells the story that the rest of the dashboard proves.
It demonstrates client empathy, workflow ownership, and iteration —
the core competencies of a Distyl AI Strategist.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Engagement Narrative", layout="wide")

# Page references for st.page_link
PAGES = {
    "problem_scoping": "app/pages/1_Problem_Scoping.py",
    "prototype_lab": "app/pages/2_Prototype_Lab.py",
    "reliability_review": "app/pages/3_Reliability_Review.py",
    "abstraction_layer": "app/pages/4_Abstraction_Layer.py",
    "executive_summary": "app/pages/5_Executive_Summary.py",
    "roi_model": "app/pages/6_ROI_Model.py",
    "data_quality": "app/pages/7_Data_Quality.py",
    "human_feedback": "app/pages/8_Human_Feedback.py",
    "prompt_ab": "app/pages/9_Prompt_AB_Testing.py",
}

st.title("Engagement Narrative")
st.markdown(
    "How I would run this as a real customer engagement — "
    "from first meeting to production handoff."
)

# ---------------------------------------------------------------------------
# The Client
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("The Client")

c_left, c_right = st.columns([3, 1])
with c_left:
    st.markdown("""
**Industry:** Telecom (Top-5 US carrier)
**Scale:** 12M support tickets/year across voice, chat, email, and in-store
**Current state:** Manual classification by 800+ agents, 35% tag inconsistency rate,
6-week lag on executive reporting, zero real-time visibility into VIP churn drivers
""")
with c_right:
    st.info(
        '**The ask from their COO:**\n\n'
        '*"I need to know why we\'re losing VIP customers — not in 6 weeks, but this week. '
        'And I need to trust the answer."*'
    )

# ---------------------------------------------------------------------------
# Week-by-week engagement
# ---------------------------------------------------------------------------

st.markdown("---")
st.header("Engagement Timeline")

# ── Week 0 ──
st.subheader("Week 0: Discovery & Scoping")
w0_left, w0_right = st.columns([2, 1])
with w0_left:
    st.markdown("""
**What I did:**
- Sat with 6 frontline agents for a full day each — watched them classify tickets live
- Interviewed 3 ops managers about their reporting workflow
- Pulled 2 weeks of raw ticket exports (200K rows) to understand the data

**Key findings:**
- Agents spend **15 min/ticket** on classification — 8 min reading, 5 min tagging, 2 min routing
- The same ticket type gets tagged 4 different ways depending on which agent handles it
- "VIP churn risk" is tracked in a spreadsheet updated monthly by one person
- 30% of tickets are in German or mixed-language — current taxonomy is English-only

**Decision I made:**
> AI should structure the data, not replace the agents. The agents know the domain —
> the system should make their knowledge consistent and queryable.
""")
with w0_right:
    st.markdown("**Artifacts delivered:**")
    st.page_link(PAGES["problem_scoping"], label="Problem Scoping matrix", icon="📋")
    st.page_link(PAGES["data_quality"], label="Data Quality report", icon="📊")
    st.markdown("---")
    st.metric("Time spent with users", "6 days")
    st.metric("Pain points identified", "12")
    st.metric("AI-appropriate problems", "7 of 12")

st.markdown("---")

# ── Week 1-2 ──
st.subheader("Week 1–2: Build & Validate")
w1_left, w1_right = st.columns([2, 1])
with w1_left:
    st.markdown("""
**What I built:**
- Extraction pipeline: Raw text → Normalized → LLM structured JSON → Validated → Gated → Stored
- 7 gate rules encoding the client's own risk policies (from their compliance team)
- Evidence grounding requirement: every classification must cite source text

**How I validated:**
- Ran 10 diverse cases through Claude Sonnet — not cherry-picked, selected for difficulty
- Sat with 2 senior agents to review every extraction side-by-side with the source ticket
- They caught: 1 hallucinated evidence quote, 2 overconfident short-input cases, 1 risk underestimate

**What I changed based on their feedback:**
- Added **prompt v2**: short-input confidence cap (< 30 words → max 0.7 confidence)
- Zero code changes — one prompt line fixed the issue
- Re-ran same 10 cases: short inputs fixed, long inputs unaffected
""")
with w1_right:
    st.markdown("**Artifacts delivered:**")
    st.page_link(PAGES["prototype_lab"], label="Prototype Lab", icon="🔬")
    st.page_link(PAGES["reliability_review"], label="Reliability & Review", icon="🛡️")
    st.page_link(PAGES["prompt_ab"], label="Prompt A/B Testing", icon="🔄")
    st.markdown("---")
    st.metric("Schema pass rate", "100%", help="10/10 real-model extractions pass JSON schema")
    st.metric("Evidence grounding", "97.3%", help="36/37 quotes verbatim from source text")
    st.metric("Prompt iterations", "2 (v1 → v2)")

st.markdown("---")

# ── Week 3 ──
st.subheader("Week 3: User Adoption & Iteration")
w2_left, w2_right = st.columns([2, 1])
with w2_left:
    st.markdown("""
**What I did:**
- Onboarded 5 agents to the Human Feedback page as reviewers
- They reviewed 15 cases over 3 days — approving or correcting each extraction
- Tracked human-AI agreement rate: **90% field-level agreement**
- Most corrected fields: `root_cause_l1` and `risk_level` — these became prompt v3/v4 targets

**The adoption moment:**
> After Day 2, one agent said: *"I used to spend 15 minutes per ticket. Now I spend 2 minutes
> checking the AI output and fixing the risk level. I actually trust the root cause now."*

**What this proved:**
- The system doesn't replace agents — it gives them a **pre-filled, auditable starting point**
- Human corrections feed back into evaluation → the system learns what it gets wrong
- Agreement rate is a **measurable product metric**, not a vague "users like it"
""")
with w2_right:
    st.markdown("**Artifacts delivered:**")
    st.page_link(PAGES["human_feedback"], label="Human Feedback loop", icon="👤")
    st.markdown("---")
    st.metric("Cases reviewed", "15")
    st.metric("Human-AI agreement", "90%")
    st.metric("Avg review time", "2 min/case", delta="-13 min vs manual", delta_color="inverse")

st.markdown("---")

# ── Week 4 ──
st.subheader("Week 4: Executive Delivery & Handoff")
w3_left, w3_right = st.columns([2, 1])
with w3_left:
    st.markdown("""
**What I delivered to the COO:**
- Executive Summary: one-glance view of churn drivers, VIP risk, automation rate
- ROI Model: interactive cost projection showing **$1.2M/year savings** at their scale
- Clear roadmap for production: parallel extraction, feedback loops, SSO integration

**The COO's reaction:**
> *"This is the first time I've seen a churn driver report I actually trust —
> because I can click through to the evidence."*

**What made this different from a typical AI demo:**
- Every number has a source. Every classification has evidence quotes.
- The system says "I don't know" (sends to review) instead of guessing.
- The dashboard shows **coverage rate and uncertainty** — not just pretty charts.
- Human corrections are logged and used to improve the next iteration.
""")
with w3_right:
    st.markdown("**Artifacts delivered:**")
    st.page_link(PAGES["executive_summary"], label="Executive Summary", icon="📈")
    st.page_link(PAGES["roi_model"], label="ROI Model", icon="💰")
    st.page_link(PAGES["abstraction_layer"], label="Abstraction Layer", icon="🧩")
    st.markdown("---")
    st.metric("Projected annual savings", "$1.2M")
    st.metric("Time-to-insight", "Real-time", delta="vs 6-week lag", delta_color="inverse")
    st.metric("Deployment success rate", "100%")

st.markdown("---")

# ---------------------------------------------------------------------------
# Why this matters for Distyl
# ---------------------------------------------------------------------------

st.header("Why This Engagement Pattern Fits Distyl")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("#### Earn Customer Trust")
    st.markdown(
        "I spent 6 days with frontline agents before writing a single line of code. "
        "The system reflects *their* domain knowledge — they saw their own language "
        "in the evidence quotes. Trust comes from understanding the workflow better "
        "than the users expect."
    )

with col_b:
    st.markdown("#### Own Business Outcomes")
    st.markdown(
        "The deliverable wasn't a model or a dashboard — it was the answer to "
        "'why are we losing VIP customers?' backed by auditable evidence. "
        "Every technical decision (gate rules, confidence caps, evidence requirements) "
        "maps to a business outcome: accuracy, trust, or efficiency."
    )

with col_c:
    st.markdown("#### Drive User Adoption")
    st.markdown(
        "Adoption isn't a launch event — it's a feedback loop. "
        "The Human Feedback page proves that users engage with the system, "
        "their corrections improve it, and agreement rate is a measurable signal "
        "that the product is valuable. This is iteration, not deployment."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Honest retrospective
# ---------------------------------------------------------------------------

st.header("Honest Retrospective")

ret_good, ret_change, ret_next = st.columns(3)

with ret_good:
    st.markdown("#### What went well")
    st.markdown("""
- Evidence grounding — 97% of quotes are verbatim from source text
- Gate logic accurately separates safe vs. risky cases (50/50 split)
- Prompt iteration cycle works: observe → hypothesize → change → measure
- ROI model with adjustable assumptions — not a fixed pitch
""")

with ret_change:
    st.markdown("#### What I'd change")
    st.markdown("""
- Should have built the feedback loop in Week 1, not Week 3
- Need a controlled L2 taxonomy — free-text sub-categories drift over time
- German handling works but wasn't systematically evaluated
- Mock data makes the demo less convincing than real-model data
""")

with ret_next:
    st.markdown("#### What's next")
    st.markdown("""
- Gold labels: have agents annotate 100 cases for precision/recall
- Parallel extraction: 40 cases in ~30s instead of ~5 min
- Multi-turn conversations: current system processes single tickets only
- Production auth, role-based views, CRM integration
""")

st.markdown("---")
st.caption(
    "This page describes a simulated engagement. The system, pipeline, evaluation, "
    "and feedback data are real — built to the standard a client would see in Week 2 "
    "of a real deployment."
)
