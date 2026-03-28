# Forward-Deployed AI Simulation

> "This is a forward-deployed AI simulation that turns noisy enterprise support data into structured operational insight, with reliability controls and reusable abstractions."

---

## Why this project

Most AI demos stop at "call an LLM and show the output." This project goes further — it simulates the full loop that a forward-deployed AI team actually runs:

1. **Pick a real problem** (not a toy benchmark)
2. **Decide where AI should and should not be used** (before writing code)
3. **Build a system, not a model call** (extraction + validation + gating + storage + audit)
4. **Measure it** (evaluation harness with failure mode detection)
5. **Abstract it** (reusable modules that transfer across industries)

The result is not a chatbot. It is an AI-augmented operational workflow with reliability controls, human-in-the-loop review, and measurable quality.

---

## The client problem

Large enterprises — telecom, financial services, contact centers — generate massive volumes of unstructured text every day: support tickets, emails, chat conversations, resolution notes. This data is:

- **Noisy**: multilingual, abbreviated, emotionally charged, full of typos
- **Fragmented**: scattered across ticket systems, email, knowledge bases, and spreadsheets
- **Invisible to management**: C-suite can't answer "what are the top VIP churn drivers?" without weeks of manual analysis
- **Manually classified**: frontline agents tag tickets by experience and instinct, producing inconsistent labels

The gap between raw text and actionable insight is where the value is.

---

## Why AI here — and where AI should not be used

Not every step should be automated. This project defines explicit boundaries:

| Task | AI Suitability | Control |
|------|---------------|---------|
| Text cleanup and normalization | **High** | Rules + lightweight model |
| Root cause / intent classification | **High** | Structured JSON output + confidence score + sampling audit |
| Sentiment and risk signal extraction | **Medium** | Must output evidence paragraph; never auto-attributes blame |
| Actionable recommendation generation | **Medium** | Must cite source text; high-risk categories require mandatory human review |
| Auto-reply to customers or SLA promises | **Blocked** | Not permitted. Draft only, human sends. |
| Executive insight (VIP churn drivers, top risks) | **High** (conditional) | Must display data coverage rate, missing rate, and uncertainty |

This matrix was written before any code. It defines the system boundary.

---

## Current workflow (before)

```
Raw Tickets / Emails / Chats
  → Frontline agent reads manually
  → Manual tagging and routing (inconsistent)
  → Manual investigation / SME escalation
  → Resolution notes (free text, unstructured)
  → Weekly or monthly reporting (lagging by weeks)
  → C-suite decisions (low visibility, anecdotal)
```

The problem is structural: there is no layer between raw text and management decisions that is consistent, auditable, or fast.

---

## Proposed workflow (after)

```
Raw Tickets / Emails / Chats
  → Ingestion and normalization
  → LLM structuring (forced JSON schema output)
  → Post-validation (schema check + evidence coverage)
  → Risk / confidence gate
      ├─ Low risk, high confidence  → Auto-route + draft recommendation
      └─ High risk OR low confidence → Human review queue
  → Structured store (SQLite + JSONL trace log)
  → Dashboard (root cause × churn × VIP cross-tabs)
  → Evaluation harness (metrics + failure mode detection)
```

AI does structuring and candidate suggestions. The system does gating and routing. Humans make high-risk decisions and provide feedback. Every step is logged.

---

## System design

The pipeline processes one case bundle at a time through six stages:

```
CaseBundle → Normalize → LLM Extract → Validate → Gate → Store
                                                      ↓
                                                 Trace Log
                                                      ↓
                                                 Eval Harness
```

**Key design decisions:**

- **Provider interface**: LLM extraction uses a `Protocol`-based interface. Swap Claude for GPT-4 or a fine-tuned model by implementing one method. No pipeline code changes.
- **Forced structured output**: The prompt requires JSON conforming to `EXTRACTION_SCHEMA`. If the LLM returns invalid JSON, a fallback parser attempts recovery. If that fails, the case is routed to review with `review_required=true`.
- **Evidence is mandatory**: Every extraction must include `evidence_quotes` — exact phrases from the source text. If evidence is missing, the case cannot be auto-finalized.
- **Dual-write storage**: SQLite for queryable aggregates (root cause × churn × VIP) and JSONL for append-only audit trail. Trace logs capture: case_id, timestamp, model name, prompt version, validation result, gate decision, reason codes, latency, and raw LLM response.
- **No silent failures**: Schema validation errors, evidence gaps, and gate decisions are logged with specific reason codes, not swallowed.

---

## Reliability and review logic

Seven rules determine whether a case is auto-routed or sent to human review. Any single trigger sends the case to review.

| # | Rule | Threshold | Reason code |
|---|------|-----------|-------------|
| 1 | Low confidence | < 0.7 | `low_confidence` |
| 2 | High churn risk | >= 0.6 | `high_churn_risk` |
| 3 | High or critical risk level | high, critical | `high_risk_level` |
| 4 | Model flagged review | review_required = true | `model_flagged` |
| 5 | High-risk root cause category | security_breach, outage, vip_churn, data_loss | `high_risk_category` |
| 6 | Missing evidence | evidence_quotes empty | `missing_evidence` |
| 7 | Ambiguous root cause | unknown, ambiguous, other | `ambiguous_root_cause` |

The gate returns `route` (auto or review), `reasons` (human-readable), and `review_reason_codes` (machine-readable). Reason codes are stored in SQLite, enabling dashboard breakdowns and rule tuning.

**Non-negotiable**: A case with `review_required=true` is never auto-finalized. A case with missing evidence is never auto-finalized. These rules are enforced in code, not policy.

---

## Evaluation results

Evaluation was run on 35 case bundles using the mock provider (which returns identical extractions for every case — this is intentional, to stress-test the eval harness).

### Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Schema pass rate | 100% | >= 98% | **PASS** |
| Evidence coverage rate | 100% | >= 90% | **PASS** |
| Unsupported recommendation rate | 0% | <= 2% | **PASS** |
| Root cause consistency | 100% | >= 70% | **PASS** |

### Failure modes detected

| Mode | Count | What it caught |
|------|-------|---------------|
| **Hallucination** | 23 | Mock evidence quote "I was charged twice" doesn't appear in 23/35 source texts — correctly flagged |
| **Omission** | 3 | Cases with "legal action" or "outage" signals in text, but mock returned risk_level=medium — correctly flagged |
| **Ambiguity** | 0 | No short-ticket + high-confidence mismatches with mock |
| **Overconfidence** | 0 | No gold labels to compare against with mock |
| **Language drift** | 0 | All mock cases processed as English |

The failure mode counts are not flaws — they prove the evaluation harness works. The hallucination detector correctly identifies that a fixed evidence quote doesn't match 23 different source texts. The omission detector correctly catches 3 cases where urgent signals were ignored. With a real LLM, these detectors will catch real failures.

---

## Abstraction and transferability

The system decomposes into six reusable modules, each with a defined interface:

| Module | What it does | Key file(s) |
|--------|-------------|-------------|
| **Ingestion Layer** | Multi-source text + metadata → normalized case bundle | `pipeline/loaders.py`, `normalize.py` |
| **Semantic Structuring Engine** | Case bundle + schema → structured extraction with evidence | `pipeline/extract.py`, `schemas.py` |
| **Risk & Review Router** | Extraction + rules → gate decision with reason codes | `pipeline/gate.py` |
| **Observability & Audit Trail** | Pipeline run → SQLite + JSONL trace with full provenance | `pipeline/storage.py` |
| **Evaluation Harness** | Predictions + cases → metrics, failure modes, markdown report | `eval/metrics.py`, `failure_modes.py`, `run_eval.py` |
| **Decision Dashboard** | Structured data → 4-page Streamlit app for 3 personas | `app/` |

**To apply this to a new domain**, change three things:
1. The case bundle schema (what fields does one "case" have?)
2. The extraction schema (what structured signals do you need?)
3. The gate rules (what thresholds and categories apply?)

Everything else — the pipeline, validation, storage, eval harness, dashboard — works as-is.

**Adjacent use cases:**

| Domain | Input | Structuring task |
|--------|-------|-----------------|
| Insurance claims | Claims forms, adjuster notes | Classification, missing document detection, fraud signals |
| Healthcare triage | Intake notes, symptom descriptions | Risk stratification, urgency routing, specialist matching |
| E-commerce returns | Return requests, customer messages | Root cause attribution, defect aggregation |
| Internal IT support | IT tickets, system logs | Incident classification, impact assessment, escalation routing |

Full detail: [`docs/abstraction.md`](docs/abstraction.md)

---

## Repo structure

```
forward-deployed-ai-sim/
├── app/                          # Streamlit UI (4 pages)
│   ├── Home.py                   # System status + navigation
│   └── pages/
│       ├── 1_Problem_Scoping.py  # AI suitability matrix, success criteria
│       ├── 2_Prototype_Lab.py    # Case selector, extraction, gate decision
│       ├── 3_Reliability_Review.py  # Review queue, reason codes, audit trail
│       └── 4_Abstraction_Layer.py   # Modules, interfaces, adjacent use cases
├── pipeline/                     # Core processing
│   ├── schemas.py                # CaseBundle + ExtractionOutput dataclasses + JSON schemas
│   ├── loaders.py                # Load/save case bundles, CSV/JSONL readers
│   ├── normalize.py              # Text cleanup, language detection
│   ├── extract.py                # LLM extraction (Claude provider + mock + fallback)
│   ├── validate.py               # Schema validation + evidence coverage check
│   ├── gate.py                   # 7 review rules with reason codes
│   └── storage.py                # SQLite (3 tables) + JSONL trace log
├── eval/                         # Evaluation
│   ├── metrics.py                # 5 metrics with pass/fail targets
│   ├── failure_modes.py          # 5 failure mode detectors
│   └── run_eval.py               # Batch eval + markdown report generator
├── scripts/                      # CLI tools
│   ├── ingest_data.py            # Download datasets (HTTP + synthetic fallback)
│   ├── build_cases.py            # Assemble 35 case bundles
│   └── run_pipeline.py           # Full pipeline: load → extract → validate → gate → store
├── tests/                        # 71 tests across 6 files
├── data/
│   ├── cases/                    # 35 case bundle JSON files
│   └── eval/                     # Evaluation report
├── docs/
│   ├── project_brief.md          # Phase 0: locked project shape
│   ├── abstraction.md            # Reusable modules + adjacent use cases
│   ├── experiment_log.md         # Experiment tracking
│   └── demo_script.md            # 2-min and 5-min interview narratives
├── CLAUDE.md                     # Operating instructions for Claude Code
├── requirements.txt
└── README.md                     # This file
```

---

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Step 1: Download/generate raw data
PYTHONPATH=. python scripts/ingest_data.py

# Step 2: Build case bundles
PYTHONPATH=. python scripts/build_cases.py

# Step 3: Run the pipeline (--mock for demo without API key)
PYTHONPATH=. python scripts/run_pipeline.py --mock

# Step 4: Run evaluation and generate report
PYTHONPATH=. python -m eval.run_eval --cases data/cases --mock --report data/eval/report.md

# Step 5: Launch the dashboard
PYTHONPATH=. streamlit run app/Home.py

# Run tests
python -m pytest tests/ -v
```

To use the real Claude API instead of mock:
```bash
export ANTHROPIC_API_KEY=your-key-here
PYTHONPATH=. python scripts/run_pipeline.py
```

---

## Data and licensing

| Dataset | License | Repo policy |
|---------|---------|-------------|
| [SAMSum](https://huggingface.co/datasets/knkarthick/samsum) | CC BY-NC-ND 4.0 | Download scripts only; no raw text committed |
| [Enron Email](https://www.cs.cmu.edu/~enron/) | Public (FERC release) | Sampled + de-identified at runtime |
| [Support Tickets (HF)](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) | CC BY-NC 4.0 | Primary ticket baseline |
| Synthetic fallback | N/A | 30 tickets + 10 conversations generated when API is unavailable |
