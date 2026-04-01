# Forward-Deployed AI Simulation

**An end-to-end system that turns noisy enterprise support data into structured operational insight — with reliability controls, human-in-the-loop review, and measurable iteration.**

This is not a chatbot or a model demo. It simulates a 4-week forward-deployed AI engagement: from raw data discovery to executive-ready dashboards, with the evaluation discipline and feedback loops that production systems require.

---

## Why This Exists

Large enterprises generate thousands of support interactions daily. The data is noisy (multilingual, abbreviated, emotionally charged), fragmented (scattered across systems), and invisible to management. A COO cannot answer "what are the top VIP churn drivers this quarter?" without weeks of manual analysis.

This project fills that gap with structured AI extraction backed by reliability controls — built to the standard a client would see in Week 2 of a real deployment.

---

## Key Results

| Metric | Result | How |
|--------|--------|-----|
| Schema pass rate | **100%** (10/10 real cases) | Forced JSON output + jsonschema validation |
| Evidence grounding | **97.3%** (36/37 quotes verbatim) | Prompt instructs exact-quote extraction, verified by substring match |
| Human-AI agreement | **90%** field-level | 15 cases reviewed by simulated agents, corrections tracked |
| Prompt iteration | **v1 → v2**, zero code changes | One prompt line fixed overconfidence on short inputs |
| Gate routing | **50/50** auto/review split | 7 rules encoding risk policies: confidence, churn, severity, evidence |

---

## 2-Minute Walkthrough

**Start with the [Engagement Narrative](app/pages/0_Engagement_Narrative.py)** — it tells the story of a 4-week client engagement:

- **Week 0: Discovery** — Sat with frontline agents, pulled raw data, scoped the AI opportunity
- **Week 1-2: Build & Validate** — Pipeline + 10-case real eval + prompt iteration based on user feedback
- **Week 3: User Adoption** — Onboarded reviewers, tracked 90% human-AI agreement, identified prompt improvement targets
- **Week 4: Executive Delivery** — COO dashboard, ROI model ($1.2M/year projected savings), production roadmap

Then explore the 10-page dashboard:

| Page | What It Shows |
|------|--------------|
| **Engagement Narrative** | Week-by-week client engagement story |
| **Problem Scoping** | AI suitability matrix, what AI should/shouldn't do |
| **Prototype Lab** | Pick a case, see raw input vs. structured extraction |
| **Reliability & Review** | Gate distribution, reason codes, confidence charts |
| **Abstraction Layer** | Reusable modules, adjacent use cases |
| **Executive Summary** | Churn drivers, VIP risk, automation rate |
| **ROI Model** | Interactive cost-benefit with adjustable assumptions |
| **Data Quality** | Input EDA: noise signals, text lengths, multilingual analysis |
| **Human Feedback** | Review AI outputs, correct errors, agreement analytics |
| **Prompt A/B Testing** | v1 vs v2 metrics comparison, iteration framework |

---

## Architecture

```
Raw text → Normalize → LLM Extract (forced JSON) → Validate → Gate → Store → Dashboard
                                                     │
                                            ┌────────┴────────┐
                                            │                 │
                                       Auto-route       Human review
                                    (low risk, high     (high risk, low
                                     confidence)        confidence, or
                                                        missing evidence)
                                            │                 │
                                            └────────┬────────┘
                                                     │
                                              Feedback loop
                                         (corrections → eval → prompt iteration)
```

Every step is logged. Every extraction includes evidence quotes. Every gate decision records machine-readable reason codes. Every human correction feeds back into evaluation.

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Step 1: Download real datasets
PYTHONPATH=. python scripts/ingest_data.py

# Step 2: Build 40 case bundles
PYTHONPATH=. python scripts/build_cases.py

# Step 3: Run pipeline
PYTHONPATH=. python scripts/run_pipeline.py --mock

# Step 4: Seed demo feedback data
PYTHONPATH=. python scripts/seed_feedback.py

# Step 5: Launch dashboard
PYTHONPATH=. streamlit run app/Home.py

# Run tests (82 tests)
python -m pytest tests/ -v
```

For real model extraction (requires API key):
```bash
export ANTHROPIC_API_KEY=your-key-here
PYTHONPATH=. python scripts/run_pipeline.py
```

---

## Tech Stack

- **Python 3.11+** — pipeline, evaluation, dashboard
- **Streamlit** — 10-page interactive dashboard
- **Claude API** via `anthropic` SDK — structured extraction with JSON schema
- **SQLite** — queryable aggregates (root cause x churn x VIP)
- **JSONL** — immutable trace logs and feedback audit trail
- **pytest** — 82 tests across 7 test files

---

## Data

Two real public datasets downloaded at runtime via HuggingFace API:
- [Tobi-Bueck/customer-support-tickets](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) — multilingual (EN/DE) support tickets
- [bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) — customer-agent dialogue pairs

40 case bundles assembled from real text with labeled synthetic metadata (VIP tier, churn label — deterministic, seed=42). No raw dataset files committed to repo.

---

## Repo Structure

```
forward-deployed-ai-sim/
├── app/                            # Streamlit dashboard (10 pages + Home)
├── pipeline/                       # Core: schemas, extract, validate, gate, storage, feedback
├── eval/                           # Metrics, failure modes, batch evaluation
├── scripts/                        # Ingest, build cases, run pipeline, seed feedback
├── tests/                          # 82 tests across 7 files
├── data/cases/                     # 40 case bundle JSON files
├── data/eval/                      # Real-model evaluation reports
└── docs/                           # Project brief, demo script, inspection report
```
