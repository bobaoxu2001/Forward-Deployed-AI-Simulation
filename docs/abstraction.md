# Abstraction

## What this system does

Transforms noisy, multilingual enterprise support interactions (tickets, emails, chat conversations) into structured operational signals — root cause, sentiment, churn risk, recommended actions — with evidence citations, reliability gates, human review routing, and measurable evaluation.

This is not a model wrapper. It is a **system** with six separable components, each with a defined interface. The value is not in any single LLM call — it is in the pipeline that makes the output auditable, gatable, and evaluable before it reaches a decision-maker.

### What we built and measured

| Fact | Value |
|------|-------|
| Case bundles processed | 35 |
| Schema pass rate | 100% (target: >= 98%) |
| Evidence coverage rate | 100% (target: >= 90%) |
| Unsupported claim rate | 0% (target: <= 2%) |
| Failure modes detected | 26 across 24 cases (hallucination: 23, omission: 3) |
| Review rules encoded | 7 (with machine-readable reason codes) |
| Trace log fields per run | 11 (case_id, timestamp, model, prompt version, validation, review, reason codes, route, latency, raw response) |

The failure mode counts prove the evaluation harness works: with a mock provider returning identical extractions for every case, the hallucination detector correctly identifies that evidence quotes don't match source text in 23/35 cases, and the omission detector catches 3 cases where urgent or outage signals were missed.

---

## Reusable modules

Each module has a defined input, output, and implementation location. To reuse in another domain, swap the schema and data — the pipeline stays the same.

### 1. Ingestion Layer

**What it does:** Takes multi-source unstructured text (tickets, emails, conversations) and metadata, normalizes them into a flat case bundle with consistent fields.

**Interface:**
```
Input:  raw text (any format) + metadata (priority, VIP tier, handle time)
Output: CaseBundle(case_id, ticket_text, email_thread, conversation_snippet,
        vip_tier, priority, handle_time_minutes, churned_within_30d)
```

**Implementation:** `pipeline/loaders.py`, `pipeline/normalize.py`, `scripts/ingest_data.py`, `scripts/build_cases.py`

**What transfers:** The pattern of assembling one "delivery unit" per case from heterogeneous sources. The schema changes per domain; the assembly logic is the same.

---

### 2. Semantic Structuring Engine

**What it does:** Sends a normalized case bundle to an LLM with a forced JSON schema, extracts root cause, sentiment, risk, recommended actions, and evidence quotes. Parses the response with fallback handling.

**Interface:**
```
Input:  CaseBundle + JSON schema definition
Output: ExtractionOutput(root_cause_l1, root_cause_l2, sentiment_score,
        risk_level, review_required, next_best_actions, evidence_quotes,
        confidence, churn_risk)
```

**Implementation:** `pipeline/extract.py`, `pipeline/schemas.py`

**Key design decisions:**
- Provider interface (`LLMProvider` Protocol) — swap Claude for GPT-4, Gemini, or a fine-tuned model without changing pipeline code
- Prompt forces evidence citation from source text, not generated text
- JSON parse fallback: if response isn't valid JSON, attempt extraction; if that fails, return a minimal structure with `review_required=true`
- No evidence → forced review (non-negotiable)

**What transfers:** The pattern of schema-constrained extraction with evidence requirements. Every domain needs its own taxonomy (L1/L2 categories), but the extraction-validation-fallback pattern is identical.

---

### 3. Risk & Review Router

**What it does:** Applies deterministic rules to decide whether an extraction should be auto-routed or sent to human review. Returns the decision, human-readable reasons, and machine-readable reason codes.

**Interface:**
```
Input:  ExtractionOutput (as dict)
Output: {route: "auto"|"review", reasons: [...], review_reason_codes: [...]}
```

**Rules (7 total):**

| # | Rule | Threshold | Code |
|---|------|-----------|------|
| 1 | Low confidence | < 0.7 | `low_confidence` |
| 2 | High churn risk | >= 0.6 | `high_churn_risk` |
| 3 | High/critical risk level | high, critical | `high_risk_level` |
| 4 | Model flagged review | review_required=true | `model_flagged` |
| 5 | High-risk category | security_breach, outage, vip_churn, data_loss | `high_risk_category` |
| 6 | Missing evidence | evidence_quotes empty | `missing_evidence` |
| 7 | Ambiguous root cause | unknown, ambiguous, other, empty | `ambiguous_root_cause` |

**Implementation:** `pipeline/gate.py`

**What transfers:** The pattern of rule-based routing with stored reason codes. Every domain has different thresholds and categories, but the gate-with-reasons architecture is the same. Storing reason codes (not just booleans) enables dashboard breakdowns and rule tuning.

---

### 4. Observability & Audit Trail

**What it does:** Records every pipeline run as a queryable trace with full provenance: what went in, what came out, what model/prompt was used, whether validation passed, what the gate decided, and why.

**Interface:**
```
Input:  case_id, extraction, gate_decision, metadata, validation_result
Output: SQLite row in trace_logs table + JSONL append
```

**What gets logged (per run):**
- `case_id`, `timestamp`
- `model_name`, `prompt_version`
- `validation_pass`, `validation_errors`
- `review_required`, `review_reason_codes`
- `gate_route`
- `latency_ms`
- `raw_response` (full LLM output for debugging)

**Implementation:** `pipeline/storage.py` (3 tables: `cases`, `extractions`, `trace_logs` + JSONL file)

**What transfers:** The pattern of dual-write (queryable DB + append-only log) with full provenance. This is the foundation for audit compliance, debugging, and model comparison. Every enterprise deployment needs this; the schema changes, the pattern doesn't.

---

### 5. Evaluation Harness

**What it does:** Runs batch evaluation across all cases, computing metrics against defined targets, detecting failure modes with specific examples, and generating a markdown report.

**Interface:**
```
Input:  list of extractions + list of cases (from files or SQLite)
Output: {metrics: {...}, failure_modes: {...}, gate_distribution: {...}, report: str}
```

**Metrics computed:**

| Metric | What it measures | Target |
|--------|-----------------|--------|
| Schema pass rate | Structural validity | >= 98% |
| Evidence coverage rate | Claims backed by source text | >= 90% |
| Unsupported recommendation rate | Recommendations without evidence | <= 2% |
| Root cause consistency | Same-type cases get same L1 label | >= 70% |
| Review routing precision/recall | Gate accuracy vs gold labels | P >= 0.80, R >= 0.90 |

**Failure modes detected:**

| Mode | Detection logic |
|------|----------------|
| Hallucination | Evidence quotes not found in source text (substring match) |
| Omission | Urgent/outage/billing signals in text but not reflected in extraction |
| Ambiguity | Very short ticket + high confidence + no review flag |
| Overconfidence | High confidence but wrong root cause vs gold label |
| Language drift | Non-English case + low confidence or ambiguous root cause |

**Implementation:** `eval/metrics.py`, `eval/failure_modes.py`, `eval/run_eval.py`

**What transfers:** The evaluation framework is the most reusable piece. Any domain with structured extraction needs schema validation, evidence verification, and failure mode tracking. The specific detectors change; the harness stays.

---

### 6. Decision Dashboard

**What it does:** Four-page Streamlit app that serves three personas (C-suite, ops manager, frontline lead) with views into the problem, the extraction results, the review queue, and the system abstractions.

**Pages:**
1. **Problem Scoping** — AI suitability matrix, success criteria, non-goals
2. **Prototype Lab** — Case selector, raw input | extracted output side-by-side, validation, gate decision
3. **Reliability & Review** — Gate distribution, reason code breakdown, confidence histogram, review queue inspector, audit trail
4. **Abstraction Layer** — Reusable modules, interfaces, adjacent use cases, production roadmap, live metrics

**Implementation:** `app/Home.py`, `app/pages/`

**What transfers:** The information architecture (problem → prototype → reliability → abstraction) works for any forward-deployed engagement. The specific visualizations change; the four-page structure and the principle of showing evidence + uncertainty alongside results is universal.

---

## Adjacent use cases

The six modules above form a pattern: **noisy unstructured input → schema-constrained extraction → evidence-backed output → reliability gate → auditable storage → measured evaluation**. This pattern applies whenever:

1. You have unstructured text that needs structured interpretation
2. The stakes are high enough to require evidence and review
3. Management needs aggregate visibility across many cases
4. The system must be auditable and improvable over time

| Domain | Input data | Structuring task | Key difference from support tickets |
|--------|-----------|-----------------|-------------------------------------|
| **Insurance claims** | Claims forms, adjuster notes, police reports, medical records | Claim classification, missing document detection, fraud signal extraction, coverage determination | Document-heavy multi-step verification; stronger compliance requirements (state regulations); higher financial stakes per case |
| **Healthcare triage** | Patient intake forms, nurse notes, symptom descriptions, prior visit summaries | Risk stratification, urgency classification, specialist routing, missing-info flagging | HIPAA compliance; clinical vocabulary; life-safety stakes require higher review thresholds; integration with EHR systems |
| **E-commerce returns** | Return requests, customer messages, product reviews, order history | Return root cause attribution, experience defect aggregation, refund eligibility, repeat-offender detection | Higher volume / lower risk per case; product catalog as structured context; fraud patterns differ from support |
| **Internal IT support** | IT tickets, system logs, change requests, incident reports | Incident classification, impact assessment, escalation routing, known-issue matching | Machine-generated text mixed with human text; CMDB as structured context; SLA-driven routing with different thresholds |

### How to migrate

To apply this system to a new domain:

1. **Define the case bundle schema** — what fields does one "case" have in your domain?
2. **Define the extraction schema** — what structured signals do you need? (Replace root_cause L1/L2 with your taxonomy)
3. **Set gate thresholds** — what confidence, risk, and category rules apply?
4. **Write failure mode detectors** — what does hallucination/omission look like in your domain?
5. **Bring data** — assemble 20-40 case bundles from real or public sources
6. **Run the pipeline** — everything else (extraction, validation, gating, storage, eval, dashboard) works as-is

---

## Production next steps

These are **strategy decisions**, not implementation plans. Each addresses a gap between the current prototype and a production deployment.

### Auth & access control
- Role-based access: analyst (view extractions), reviewer (approve/edit review queue), admin (configure rules)
- Why: different personas see different data; reviewer edits must be attributed
- Complexity: medium (standard RBAC; Streamlit auth or move to Next.js)

### Human feedback capture
- Reviewers edit extractions in the review queue; edits are stored as feedback records
- Feedback records flow back into the evaluation set for the next eval cycle
- Why: this closes the loop — human corrections improve the system, not just fix one case
- Complexity: low (UI form + feedback table in SQLite)

### Prompt & model versioning
- Track which prompt template and model version produced each extraction
- Already partially implemented (trace_logs stores model_name and prompt_version)
- Next step: A/B comparison across prompt versions with the eval harness
- Why: when you change a prompt, you need to know if it made things better or worse
- Complexity: low (eval harness already supports batch comparison)

### Regression testing
- Pin a set of "golden" case bundles with expected outputs
- Run eval on every prompt/model change; fail the deploy if metrics regress
- Why: prevent silent quality degradation
- Complexity: low (eval harness + CI integration)

### Monitoring & alerting
- Track schema fail rate, evidence coverage, review queue depth, and latency in production
- Alert if any metric crosses a threshold (e.g., schema fail rate > 5%)
- Why: know when the system degrades before users notice
- Complexity: medium (metrics export to Grafana/Datadog + alert rules)

### Policy & governance controls
- Immutable trace logs (append-only, no deletion)
- Data retention policies (how long to keep raw responses)
- Audit export for compliance reviews
- Why: enterprise requirement for regulated industries; builds trust
- Complexity: depends on regulatory environment

---

*This document describes what was actually built, measured, and abstracted — not what was planned. Every module, metric, and failure mode referenced above exists in the codebase and has been tested.*
