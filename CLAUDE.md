# CLAUDE.md

## Project
This repo is a forward-deployed AI simulation for enterprise workflow intelligence.
It turns noisy support data (tickets, emails, chats) into structured operational insight
with reliability controls, human-in-the-loop review, and reusable system abstractions.

## Goal
Build a Streamlit prototype that:
1. Ingests noisy support cases (public datasets assembled into case bundles)
2. Extracts structured operational signals (root cause, sentiment, risk, next action, evidence)
3. Applies reliability/review logic (confidence gates, risk routing, evidence requirements)
4. Writes outputs to SQLite + JSONL trace logs
5. Visualizes churn/risk/root-cause insights on a dashboard
6. Documents reusable abstractions for cross-industry transfer

## Non-goals
- No production auth or user accounts
- No real CRM/Zendesk/ServiceNow integration
- No customer-facing auto-send (AI never sends messages to customers)
- No unnecessary frontend complexity (Streamlit is the UI, not React)
- No online learning or continuous training (use offline eval + feedback logs)
- No storing raw dataset files in repo (download scripts + sample IDs only)

## Tech stack
- Python 3.11+
- Streamlit (multi-page app, 4 pages)
- Claude API via `anthropic` SDK (structured output with JSON schema)
- SQLite (queryable aggregates: root-cause x churn x VIP)
- JSONL (trace logs: every pipeline run is auditable)
- jsonschema (output validation)
- pytest (testing)
- pandas (data manipulation)

## Engineering rules
- Prefer small modular Python files — one concern per file
- Every extraction output must validate against `pipeline/schemas.py`
- Every recommendation must include evidence quotes from source text
- High-risk cases must be routed to human review, never auto-finalized
- Do not silently swallow errors — fail loud, log the failure, tag the mode
- Write readable code, not clever code
- Use mock/public data only — never commit proprietary or sensitive data
- No `# type: ignore` or `noqa` without a comment explaining why
- Keep functions short — if it needs a scroll, it needs a split
- Imports at top of file, stdlib first, then third-party, then local

## Directory layout
```
forward-deployed-ai-sim/
├── app/                  # Streamlit UI
│   ├── Home.py           # Entrypoint: streamlit run app/Home.py
│   └── pages/            # 4 pages: Problem Scoping, Prototype Lab, Reliability & Review, Abstraction Layer
├── pipeline/             # Core processing logic
│   ├── schemas.py        # JSON schemas (case bundle + structured output) — source of truth
│   ├── loaders.py        # Load case bundles from JSON files
│   ├── normalize.py      # Text cleanup (whitespace, encoding, language detection)
│   ├── extract.py        # LLM structured extraction via Claude API
│   ├── validate.py       # Post-validation: schema check + evidence coverage
│   ├── gate.py           # Risk/confidence routing (auto vs review)
│   └── storage.py        # SQLite writes + JSONL trace logging
├── eval/                 # Evaluation harness
│   ├── metrics.py        # Schema pass rate, evidence coverage, routing precision/recall
│   ├── failure_modes.py  # Failure mode detection: hallucination, omission, overconfidence, etc.
│   └── run_eval.py       # Batch evaluation runner
├── data/                 # Data directory (raw data NOT committed)
│   ├── raw/              # Downloaded datasets (gitignored)
│   ├── processed/        # SQLite DB + trace logs (gitignored)
│   ├── cases/            # Case bundle JSON files
│   └── eval/             # Gold labels and eval results
├── scripts/              # CLI scripts
│   ├── ingest_data.py    # Download public datasets
│   ├── build_cases.py    # Assemble case bundles from raw data
│   └── run_pipeline.py   # Run full pipeline on case bundles
├── tests/                # pytest tests
├── docs/                 # Documentation
│   ├── project_brief.md  # Phase 0: locked project shape
│   ├── PRD.md            # PRD reference summary
│   ├── experiment_log.md # Experiment tracking (E0-E4)
│   ├── abstraction.md    # Reusable modules and interfaces
│   └── demo_script.md    # 2-min and 5-min interview narratives
├── requirements.txt
├── README.md
└── CLAUDE.md             # This file
```

## Schemas (source of truth)
All schemas live in `pipeline/schemas.py`. Two schemas matter:

1. **CASE_BUNDLE_SCHEMA** — Input format. Required fields: `case_id`, `inputs.ticket_text`, `metadata`, `labels`.
2. **STRUCTURED_OUTPUT_SCHEMA** — LLM output format. Required fields: `root_cause` (l1, l2, confidence), `sentiment` (score, rationale), `risk` (churn_risk, severity, review_required), `recommendation` (next_best_actions, draft_notes), `evidence` (field, quote pairs).

If you need to change a schema, update `pipeline/schemas.py` first, then update all downstream code.

## Reliability rules (non-negotiable)
- `review_required=true` → case is NEVER auto-finalized; must have human confirmation
- Missing evidence for any key field → flag as `unsupported`, force into review queue
- High-risk categories (security_breach, outage, vip_churn, data_loss) → sampled review even at high confidence (10%)
- All human edits are written to feedback log for next eval cycle
- Confidence threshold: 0.7 (below = review)
- Churn risk threshold: 0.6 (above = review)

## Workflow
Always work in this order:
1. Inspect current files — read before writing
2. Propose a file-level plan — which files change, which are new
3. Implement the smallest working version — no gold-plating
4. Add tests — at minimum, test the happy path and one failure case
5. Summarize what changed and what remains

## Output style
- Concise — no filler, no restating the question
- Explicit assumptions — if you're guessing, say so
- No fake completeness — if something is a stub, mark it `raise NotImplementedError("Phase X")`
- Prefer `# TODO:` comments over hidden shortcuts
- When a function is a placeholder, the docstring says what it will do and which phase implements it

## Evaluation metrics (targets)
| Metric | Target |
|---|---|
| Schema pass rate | >= 98% |
| Evidence coverage | >= 90% |
| Review routing precision | >= 0.8 |
| Review routing recall | >= 0.9 |
| Unsupported claim rate | <= 2% |
| Recommendation usefulness | >= 3.5/5 |

## Failure modes to track
Every eval run must check for these (at least 2 examples each):
- **Hallucination** — output with no evidence quote
- **Omission** — clear signal in text but missing from output
- **Overconfidence** — high confidence on wrong classification
- **Ambiguity** — genuinely uncertain, system should say "unsure"
- **Language/format drift** — multilingual or format shifts cause collapse
- **Spurious correlation** — confounders misread as causes

## Data licensing
- SAMSum: CC BY-NC-ND 4.0 — download scripts only, no raw text in repo
- Enron Email: Public (FERC release) — sample + de-identify, download at runtime
- Support Tickets (HF): CC BY-NC 4.0 — reproducible baseline

## Commit conventions
- Short imperative subject line (e.g., "add gate logic for churn risk threshold")
- Body explains why, not what
- Reference the phase (Phase A/B/C/D) in commits when relevant
