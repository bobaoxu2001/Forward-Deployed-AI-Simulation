# CLAUDE.md — Project Instructions for Claude Code

## Project Identity

This is a forward-deployed AI simulation that turns noisy enterprise support data into structured operational insight, with reliability controls and reusable abstractions.

## Tech Stack

- **Language:** Python 3.11+
- **UI:** Streamlit (multi-page app, 4 pages)
- **LLM:** Claude API (anthropic SDK) for structured extraction
- **Storage:** SQLite (queryable aggregates) + JSONL (trace logs)
- **Data:** Public datasets (SAMSum, Enron, HF tickets) — never commit raw data
- **Testing:** pytest

## Key Conventions

- All LLM outputs must conform to JSON schemas defined in `pipeline/schemas.py`
- Every pipeline run produces a JSONL trace log entry (case_id, prompt_hash, model_id, output, validation result, gate decision, latency)
- `review_required=true` cases are never auto-finalized
- Evidence quotes are mandatory — unsupported output fields get flagged
- Evaluation metrics: schema pass rate, evidence coverage, review routing precision/recall, unsupported claim rate

## Directory Layout

- `app/` — Streamlit pages; `Home.py` is the entrypoint
- `pipeline/` — Core logic: load, normalize, extract, validate, gate, store
- `eval/` — Evaluation harness and failure mode tracking
- `data/` — Case bundles and processed outputs (raw data not committed)
- `scripts/` — CLI scripts for data ingestion, case building, pipeline execution
- `docs/` — PRD, project brief, experiment log, abstraction doc
- `tests/` — pytest tests

## Role Split

- **Human (AI Strategist):** Problem framing, success metrics, system boundaries, evaluation design, narrative
- **Claude Code:** Scaffolding, implementation, refactoring, test generation, doc drafts
- **Human-as-SME:** Reviews high-risk samples, provides feedback that flows back into eval
