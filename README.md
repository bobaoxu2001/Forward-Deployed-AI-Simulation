# Forward-Deployed AI Simulation

> "This is a forward-deployed AI simulation that turns noisy enterprise support data into structured operational insight, with reliability controls and reusable abstractions."

A Distyl-style forward-deployed delivery simulation: from messy enterprise support data (tickets, emails, chats) to auditable structured intelligence with evaluation, guardrails, and reusable system components.

## What This Is

An end-to-end AI-augmented ops workflow that:
- Extracts root cause, sentiment, risk, and next-best-action from noisy multilingual text
- Routes high-risk / low-confidence cases to human review
- Logs every decision as an auditable trace
- Measures itself with an evaluation harness and failure mode library
- Abstracts the solution into reusable modules for cross-industry transfer

## What This Is NOT

- A chatbot
- A production integration (no Zendesk/ServiceNow connectors)
- An auto-reply system (AI never sends customer-facing messages)

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app/Home.py
```

## Project Structure

```
forward-deployed-ai-sim/
├── app/                  # Streamlit multi-page UI (4 pages)
├── pipeline/             # Core extraction, validation, gating, storage
├── eval/                 # Evaluation harness, metrics, failure modes
├── data/                 # Case bundles, raw/processed data (no raw data committed)
├── scripts/              # Data ingestion, case building, pipeline runner
├── tests/                # Unit and integration tests
└── docs/                 # PRD, project brief, experiment log, abstraction doc
```

## Data & Licensing

| Dataset | License | Usage |
|---|---|---|
| [SAMSum](https://huggingface.co/datasets/knkarthick/samsum) | CC BY-NC-ND 4.0 | Prototype + eval; repo has download scripts only |
| [Enron Email](https://www.cs.cmu.edu/~enron/) | Public (privacy-sensitive) | Sampled + de-identified; downloaded at runtime |
| [Support Tickets (HF)](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) | CC BY-NC 4.0 | Primary ticket baseline |

## Phases

- **Phase 0** — Project brief locked (`docs/project_brief.md`)
- **Phase A** — Discovery + Data (problem scoping, ingestion, case bundles)
- **Phase B** — Prototype Lab (LLM structuring pipeline + validators)
- **Phase C** — Reliability + Evaluation (risk gates, review queue, eval harness)
- **Phase D** — Abstraction + Packaging (reusable modules, demo, narrative)
