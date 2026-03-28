# Project Brief

> **North star:** "This is a forward-deployed AI simulation that turns noisy enterprise support data into structured operational insight, with reliability controls and reusable abstractions."

---

## Problem

Enterprise support teams (telecom, contact centers, etc.) generate massive volumes of unstructured text — tickets, emails, chat conversations, resolution notes — that are multilingual, noisy, and fragmented across systems. Management has no timely visibility into systemic risk drivers or VIP churn causes. Manual classification is inconsistent, retrospectives are anecdotal, and metrics lag reality by weeks. The structural gap between raw text and actionable insight is where AI-augmented systems can deliver the most value — not by replacing human judgment, but by encoding it into an auditable, evaluable, iterable workflow.

## Users

| Persona | Key Questions | Success Looks Like |
|---|---|---|
| **C-suite** (COO / CXO) | "What are the top VIP churn drivers?" "Where is the highest-ROI intervention?" | One-glance dashboard with top drivers, actionable recommendations, and transparent reasoning (audit trail) |
| **Ops Manager** (customer ops lead) | "Are classifications consistent?" "Which queues are bottlenecked?" "What % requires human review and why?" | Weekly reviewable breakdown: root-cause categories, handle time, escalation rate, VIP patterns; clear human-in-the-loop ratios |
| **Frontline Support Lead** (agent / team lead) | "Can I skip manual tagging?" "Will this AI get me in trouble?" | Faster ticket handling with usable recommendations, traceable evidence quotes, and high-risk cases defaulting to human review |

## Inputs

| Input | Source | Notes |
|---|---|---|
| **Support tickets** | HuggingFace ticket datasets (primary); Kaggle (optional extension) | Contains queue, priority, language, subject, body, type, tags |
| **Email threads** | Enron Email Corpus (CMU) | Real enterprise email structure; sampled + de-identified for demo; bulk downloaded at runtime |
| **Conversation snippets** | SAMSum dataset (HuggingFace) | ~16k dialogues with human summaries; used for prototype + eval; repo stores download scripts + sample IDs only (CC BY-NC-ND 4.0) |
| **Metadata** | Synthetic augmentation on real data | VIP tier, handle time (minutes), churn label (30-day), priority, queue, language — controlled synthesis where real labels are unavailable |

These are assembled into **20-40 case bundles**, each simulating one customer/incident/problem chain (the forward-deployed delivery unit).

## Outputs

| Output | Description | Control |
|---|---|---|
| **Root cause category** | Hierarchical L1/L2 classification with confidence score | Structured JSON; confidence + sampling audit |
| **Sentiment & risk signals** | Sentiment score (-1 to 1) with rationale; churn risk (0-1); severity level | Outputs signal + evidence paragraph; no auto-attribution of blame |
| **Recommended next action** | Next-best-actions list + draft resolution notes | Must cite evidence; high-risk categories require mandatory human review |
| **Evidence quotes** | Array of (field, quote) pairs tracing each output to source text | Every key field must have at least one supporting quote; unsupported fields flagged |
| **Dashboard aggregates** | Root cause x churn x VIP cross-tabs; top drivers; trend views | Forced display of data coverage rate, missing rate, uncertainty indicators |
| **Review-required flag** | Boolean gate based on confidence, risk, and category rules | review_required=true blocks auto-routing; human must confirm before finalization |

### What AI must NOT do (explicit non-goals)
- Auto-send replies or commit SLA promises to customers (high compliance/reputation risk)
- Produce "final" conclusions without evidence citations
- Auto-finalize any case flagged review_required=true
- Replace human judgment on high-risk categories (security breach, outage, VIP churn) — even high-confidence outputs get sampled review (10%)

## Evaluation

| Dimension | Metric | Target Threshold |
|---|---|---|
| **Schema pass rate** | % of LLM outputs that validate against the structured output JSON schema | >= 98% |
| **Evidence coverage** | % of key output fields backed by at least one source-text quote | >= 90% |
| **Review routing quality** | Precision and recall of the review_required gate against gold labels | Precision >= 0.8; Recall >= 0.9 |
| **Root-cause usefulness** | Consistency across similar cases; TopN coverage of VIP churn drivers | Consistency >= 0.7; TopN coverage >= 80% |
| **Unsupported claim rate** | % of recommendations/attributions with no evidence quote | <= 2% |
| **Actionable recommendation quality** | Human-rated usefulness of suggested next actions (1-5 scale) | >= 3.5/5 |

### Failure modes to track (each with >= 2 documented examples)
- **Hallucination** — recommendation/attribution with no evidence quote
- **Omission** — clear signal in text but missing from output
- **Overconfidence** — high confidence on wrong classification, bypasses review
- **Ambiguity** — genuinely indeterminate; system must output "uncertain + needs more info"
- **Language/format drift** — multilingual or format shifts cause classification collapse
- **Spurious correlation** — dashboard conflates confounders (e.g., handle time) with root causes

---

*Phase 0 locked. No code until this brief is stable.*
