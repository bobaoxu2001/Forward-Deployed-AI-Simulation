# Forward-Deployed AI Simulation

This project simulates a forward-deployed AI engagement: turning noisy enterprise support data (tickets, emails, chats) into structured operational insight, with reliability controls and human-in-the-loop review. It is not a chatbot or a model demo. It is an end-to-end system — ingestion, extraction, validation, gating, storage, evaluation, and dashboard — built to the standard a client would see in week 2 of a real deployment.

---

## The Business Problem

Large enterprises generate thousands of support interactions daily: tickets, emails, live chats, resolution notes. This data is noisy (multilingual, abbreviated, emotionally charged), fragmented (scattered across systems), and invisible to management. A C-suite executive cannot answer "what are the top VIP churn drivers this quarter?" without weeks of manual analysis.

The gap between raw text and actionable insight is where the value is. Today that gap is filled by manual tagging — inconsistent, slow, and unauditable. This project fills it with structured AI extraction backed by reliability controls.

---

## Where AI Helps — and Where It Should Not Be Used

This matrix was defined before any code was written. It sets the system boundary.

| Task | AI Role | Control |
|------|---------|---------|
| Text cleanup and normalization | High | Rules-based, no model needed |
| Root cause / intent classification | High | Structured JSON output + confidence score + sampling audit |
| Sentiment and risk extraction | Medium | Must output evidence; never auto-attributes blame |
| Recommendation generation | Medium | Must cite source text; high-risk cases require human review |
| Auto-reply to customers | **Blocked** | AI drafts only. A human sends. |
| Executive insight (churn drivers, top risks) | High (conditional) | Must display coverage rate and uncertainty |

---

## System Workflow

**Before** (current state at most enterprises):
```
Raw text → Manual read → Manual tag → Manual escalation → Free-text notes → Monthly report
```

**After** (this system):
```
Raw text → Normalize → LLM Extract (forced JSON) → Validate → Gate → Store → Dashboard
                                                       │
                                              ┌────────┴────────┐
                                              │                 │
                                         Auto-route       Human review
                                      (low risk, high     (high risk, low
                                       confidence)        confidence, or
                                                          missing evidence)
```

Every step is logged. Every extraction includes evidence quotes from the source text. Every gate decision records machine-readable reason codes.

---

## Data

Two real public datasets, downloaded at runtime via HuggingFace API:

| Dataset | Rows Used | What It Provides | License |
|---------|-----------|-----------------|---------|
| [Tobi-Bueck/customer-support-tickets](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) | 200 | Real multilingual (EN/DE) support tickets with subject, body, agent response, priority, queue, tags | CC BY-NC 4.0 |
| [bitext/Bitext-customer-support-llm-chatbot-training-dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) | 15 (deduplicated by intent) | Customer-agent dialogue pairs with category and intent labels | Apache 2.0 |

From these, 40 case bundles are assembled. Each bundle combines real text fields (ticket body, agent response, language, priority) with explicitly labeled synthetic metadata (VIP tier, handle time, churn label — deterministic, seed=42). Field provenance is tracked in `source_dataset`.

A synthetic fallback generates data when the API is unreachable. No raw dataset files are committed to the repo.

---

## Pipeline

### Extraction

The LLM receives a case bundle and a prompt that forces structured JSON output conforming to `EXTRACTION_SCHEMA`. The prompt specifies 11 output fields: root cause (L1 + L2), sentiment score with rationale, risk level, confidence, churn risk, next best actions, evidence quotes, review flag, and draft resolution notes.

The extraction uses a `Protocol`-based provider interface. Swapping Claude for another model requires implementing one method (`extract(prompt) -> str`). No pipeline code changes.

If the LLM returns invalid JSON, a fallback parser attempts to extract `{...}` from the response. If that also fails, the case is routed to review with `confidence=0.0` and `root_cause=parse_failure`.

### Validation

Every extraction is validated against a JSON schema (`EXTRACTION_SCHEMA`) that enforces field types, enum values, numeric ranges, and `minItems` constraints on evidence quotes. Schema failures are logged, not swallowed.

Evidence presence is checked separately: every extraction must include at least one non-empty evidence quote. Missing evidence forces review regardless of confidence.

### Gate Logic

Seven rules determine whether a case is auto-routed or sent to human review:

| Rule | Trigger | Code |
|------|---------|------|
| Low confidence | < 0.7 | `low_confidence` |
| High churn risk | >= 0.6 | `high_churn_risk` |
| High/critical risk | risk level | `high_risk_level` |
| Model flagged | review_required = true | `model_flagged` |
| High-risk category | security_breach, outage, vip_churn, data_loss | `high_risk_category` |
| Missing evidence | empty quotes | `missing_evidence` |
| Ambiguous root cause | unknown, ambiguous, other | `ambiguous_root_cause` |

Any single trigger sends the case to review. The gate returns the route, human-readable reasons, and machine-readable reason codes. All are stored in SQLite for dashboard breakdowns.

### Evidence Grounding

The prompt instructs the model: "evidence_quotes MUST contain exact phrases from the case text, not your own words." The evaluation harness and dashboard both verify this by substring-matching each quote against the source text.

---

## Evaluation Results

### 3-Case Real-Provider Inspection

Three diverse cases (English ticket, German security incident, short dialogue complaint) were run through the full pipeline with Claude Sonnet to validate extraction quality after confirming pipeline plumbing with mock data.

| Dimension | Mock Provider | Real Provider |
|-----------|--------------|---------------|
| Root cause accuracy | Wrong for all 3 (fixed "billing") | Correct for all 3 (network, security_breach, service) |
| Evidence grounding | Hallucinated (quote not in source) | 11/11 quotes verbatim from source |
| Gate routing | All 3 auto-routed (incorrect) | All 3 sent to review (correct) |
| Failure modes detected | 2-3 per case | 0 |
| German handling | English evidence for German input | German evidence, English analysis |

Full report: [`docs/inspection_real_provider.md`](docs/inspection_real_provider.md)

### 10-Case Batch Evaluation

Ten cases selected for diversity (6 tickets + 4 dialogues, 8 English + 2 German, priorities low through critical, 7 to 99 words).

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Schema pass rate | 100% (10/10) | >= 98% | PASS |
| Evidence coverage | 100% (10/10) | >= 90% | PASS |
| Review-required rate | 80% (8/10) | informational | — |
| Average confidence | 0.82 | — | — |
| Average latency | 6,341 ms | — | — |
| Hallucinated quotes | 1/37 (2.7%) | <= 2% | MARGINAL |

Issues found: overconfidence on short inputs (2 of 4 cases under 15 words got confidence 0.90), one metadata line quoted as evidence.

Full report: [`data/eval/batch_10_real_provider.md`](data/eval/batch_10_real_provider.md)

### Prompt Iteration: v1 → v2

The 10-case evaluation identified that short inputs (8-14 words) received 0.90 confidence despite lacking context for high-certainty analysis. Root cause: the prompt only said "if ambiguous, set confidence below 0.7" — but short, clear text is not ambiguous, just insufficient.

**Fix:** One prompt rule added: "If the case text is very short (under ~30 words), cap confidence at 0.7 — brief inputs lack context for high-certainty analysis."

| Case | Words | v1 Confidence | v2 Confidence | Change |
|------|-------|--------------|--------------|--------|
| case-acaecb0d | 14 | 0.90 | 0.70 | -0.20 |
| case-f541aaa0 | 8 | 0.90 | 0.60 | -0.30 |
| case-652870dc | 95 | 0.90 | 0.90 | 0.00 |
| case-ac7b0b06 | 84 | 0.90 | 0.90 | 0.00 |

Short inputs fixed. Long inputs unaffected. Zero code changes — only one prompt line and a version bump.

---

## Dashboard

### Prototype Lab

Interactive case-by-case inspection. Select a case from dropdown, view raw input alongside extracted output, validation results, gate decision with reason codes, and evidence quotes with grounding verification (each quote checked against source text).

Three run modes: load existing result from DB, run mock extraction, or run real extraction via Claude API.

### Reliability & Review

Aggregate reliability view. Shows real-model evaluation metrics (parsed from batch eval report), database snapshot metrics, reason code breakdown, confidence distribution, and a full case table with `result_source` column distinguishing `real_eval` / `mock_db` / `unknown`. Includes example sections for reviewed and auto-routed cases with honest labeling of data provenance.

---

## Production Next Steps

| Step | What | Why |
|------|------|-----|
| Full 40-case real eval | Run all cases through Claude, not just 10 | Statistical significance |
| Gold labels | Human-annotated root cause + risk for 40 cases | Precision/recall measurement |
| Prompt caching | Cache identical prompts across runs | Reduce latency and cost |
| Parallel extraction | Async API calls (10 concurrent) | 40 cases in ~30s instead of ~5min |
| Feedback loop | Store human corrections, retrain eval thresholds | Continuous improvement |
| Root cause taxonomy | Controlled L2 vocabulary | Cross-run consistency |
| SSO + role-based access | Analyst vs reviewer vs executive views | Production deployment |

---

## Setup and Run

```bash
# Install
pip install -r requirements.txt

# Step 1: Download real datasets (falls back to synthetic if API unreachable)
PYTHONPATH=. python scripts/ingest_data.py

# Step 2: Build 40 case bundles
PYTHONPATH=. python scripts/build_cases.py

# Step 3: Run pipeline (mock mode — no API key needed)
PYTHONPATH=. python scripts/run_pipeline.py --mock

# Step 4: Run evaluation
PYTHONPATH=. python -m eval.run_eval --cases data/cases --mock --report data/eval/report.md

# Step 5: Launch dashboard
PYTHONPATH=. streamlit run app/Home.py

# Run tests (71 tests)
python -m pytest tests/ -v
```

For real model extraction:
```bash
export ANTHROPIC_API_KEY=your-key-here
PYTHONPATH=. python scripts/run_pipeline.py        # real extraction
```

---

## Repo Structure

```
forward-deployed-ai-sim/
├── app/                            # Streamlit dashboard (4 pages)
├── pipeline/                       # Core: schemas, extract, validate, gate, storage
├── eval/                           # Metrics, failure modes, batch evaluation
├── scripts/                        # Ingest, build cases, run pipeline
├── tests/                          # 71 tests across 6 files
├── data/cases/                     # 40 case bundle JSON files
├── data/eval/                      # Evaluation reports
├── docs/                           # Project brief, abstraction doc, demo script, inspection report
├── CLAUDE.md                       # Operating instructions for Claude Code sessions
└── README.md
```
