# Real Provider Inspection Report

> Inspection date: 2026-03-29
> Model: claude-sonnet-4-20250514 (via Anthropic Messages API)
> Prompt version: v1
> Cases inspected: 3 of 40

---

## Objective

Validate that the extraction pipeline produces correct, grounded, and auditable output when connected to a real LLM, after confirming that pipeline plumbing works correctly with a mock provider.

The mock provider returns a fixed response for every input. It is useful for testing schema validation, gate logic, storage, and failure mode detection, but it cannot test whether the system produces accurate extractions from real text. This inspection answers: **does the system actually work on real data?**

---

## Case Selection

Three cases were chosen to stress different dimensions of the pipeline:

| # | Case ID | Type | Why selected |
|---|---------|------|-------------|
| 1 | `case-4e9a11c7` | English support ticket (system outage, high priority) | Long, multi-paragraph enterprise text. Tests root cause accuracy and evidence extraction from dense input. |
| 2 | `case-ac7b0b06` | German ticket (security incident, high priority) | Entirely in German. Tests multilingual handling, evidence grounding in non-English text, and high-risk category detection. |
| 3 | `case-5f87257e` | Bitext dialogue (customer complaint, critical priority) | Short, informal ("ur work"). Tests confidence calibration on ambiguous/minimal input and dialogue-format extraction. |

---

## Side-by-Side Comparison

### Case 1: English support ticket (system outage)

| Field | Mock Provider | Real Provider |
|-------|--------------|---------------|
| root_cause_l1 | billing | **network** |
| root_cause_l2 | overcharge | **hardware_connectivity_failure** |
| sentiment_score | -0.5 | -0.6 |
| risk_level | medium | **high** |
| confidence | 0.85 | 0.80 |
| churn_risk | 0.3 | **0.7** |
| review_required | false | **true** |
| evidence_quotes | "I was charged twice for the same service" (hallucinated) | 4 quotes, all verbatim from source text |
| gate route | auto | **review** (3 reason codes) |
| failure modes detected | omission, hallucination | **none** |
| latency | 0.0 ms | 10,229 ms |

### Case 2: German ticket (security incident)

| Field | Mock Provider | Real Provider |
|-------|--------------|---------------|
| root_cause_l1 | billing | **security_breach** |
| root_cause_l2 | overcharge | **cyberattack_data_breach** |
| sentiment_score | -0.5 | -0.7 |
| risk_level | medium | **critical** |
| confidence | 0.85 | 0.9 |
| churn_risk | 0.3 | **0.8** |
| review_required | false | **true** |
| evidence_quotes | "I was charged twice..." (hallucinated, English) | 5 quotes in German, all verbatim from source |
| gate route | auto | **review** (4 reason codes) |
| failure modes detected | hallucination | **none** |
| latency | 0.0 ms | 6,865 ms |

### Case 3: Bitext dialogue (complaint)

| Field | Mock Provider | Real Provider |
|-------|--------------|---------------|
| root_cause_l1 | billing | **service** |
| root_cause_l2 | overcharge | **service quality complaint** |
| sentiment_score | -0.5 | -0.7 |
| risk_level | medium | **high** |
| confidence | 0.85 | **0.6** |
| churn_risk | 0.3 | **0.8** |
| review_required | false | **true** |
| evidence_quotes | "I was charged twice..." (hallucinated) | 2 quotes, both verbatim from source |
| gate route | auto | **review** (4 reason codes) |
| failure modes detected | hallucination | **none** |
| latency | 0.0 ms | 5,709 ms |

---

## Key Findings

### Root cause accuracy

The mock provider assigned "billing/overcharge" to all three cases regardless of content. The real provider correctly identified:
- System outage as **network / hardware connectivity failure**
- Security incident as **security_breach / cyberattack data breach**
- Customer complaint as **service / service quality complaint**

All three root causes are appropriate for the input text and match what a human analyst would assign.

### Evidence grounding

The mock provider returned a single fabricated quote ("I was charged twice for the same service") that does not appear in any of the three source texts.

The real provider returned 11 evidence quotes across the three cases. All 11 are verbatim substrings of the source text. The German case returned German-language evidence directly from the German input, confirming that the model extracts rather than translates or paraphrases.

Zero hallucination was detected by the failure mode evaluator.

### Gate routing

With the mock provider, all three cases were routed `auto` with zero reason codes, meaning no case would reach human review. This is incorrect for a system outage, a security breach, and an active customer complaint.

With the real provider, all three cases were routed `review` with the following reason codes:

| Case | Reason codes triggered |
|------|----------------------|
| System outage | `high_churn_risk`, `high_risk_level`, `model_flagged` |
| Security incident | `high_churn_risk`, `high_risk_level`, `model_flagged`, `high_risk_category` |
| Customer complaint | `low_confidence`, `high_churn_risk`, `high_risk_level`, `model_flagged` |

The gate logic correctly escalates all three cases. The security incident triggers the most rules, including the `high_risk_category` rule for `security_breach`.

### Confidence calibration

The mock provider returned 0.85 for every case. The real provider scaled confidence to input quality:

- System outage (long, detailed text): **0.80**
- Security incident (long, specific, German): **0.90**
- Customer complaint (11 words, informal): **0.60**

The short, ambiguous complaint correctly receives the lowest confidence and is the only case that triggers the `low_confidence` gate rule. This is the behavior the system was designed for: uncertain inputs get flagged.

### Multilingual handling

The German security incident (Case 2) produced:
- **German** evidence quotes (preserving the source language)
- **English** analysis fields (root cause, sentiment rationale, draft notes, next best actions)

This is the correct behavior for an enterprise system where the operations team reads English but the source data may be in any language. The evidence stays grounded in the original text; the analysis is in the operator's language.

### Latency

| Case | Latency |
|------|---------|
| System outage (long input) | 10,229 ms |
| Security incident (German, long) | 6,865 ms |
| Customer complaint (short) | 5,709 ms |
| **Average** | **7,601 ms** |

At ~7.6 seconds per case, a full 40-case batch would take approximately 5 minutes with sequential processing. This is acceptable for batch analysis but would need parallelization or caching for real-time use.

---

## Conclusion

### What this proves

The pipeline architecture works end-to-end with a real model. The separation of concerns (provider protocol, schema validation, gate logic, failure mode detection) means switching from mock to real required **zero code changes** — only a provider swap. Every layer added value:

- The **prompt** produced structured JSON output on the first attempt for all three cases, with no parse failures.
- The **schema validator** confirmed all outputs conform to `EXTRACTION_SCHEMA`.
- The **gate logic** correctly escalated all three high-risk cases to human review.
- The **failure mode detectors** found zero issues, compared with 2-3 per case under mock.
- The **evidence grounding** rule in the prompt ("only quote text that actually appears above") was followed in all cases.

### What still needs improvement

1. **Batch evaluation at scale** — This inspection covered 3 cases. The full 40-case batch needs to run to measure aggregate metrics (schema pass rate, evidence coverage, review routing precision/recall) against the evaluation targets.

2. **Root cause taxonomy** — The model generates free-text L2 categories ("hardware_connectivity_failure", "service quality complaint"). A controlled vocabulary or post-extraction normalization would improve consistency across runs.

3. **Latency** — 7.6s average per case is fine for batch but needs optimization (parallel requests, prompt caching) for interactive use in the Streamlit dashboard.

4. **Confidence calibration validation** — The model's confidence scores look reasonable on 3 cases, but there is no ground truth to measure calibration against. A labeled evaluation set would allow us to compute whether 0.6 confidence actually corresponds to ~60% accuracy.

5. **Non-English output language** — The model correctly outputs German evidence for German input, but the prompt does not explicitly specify output language. Adding `"Respond in English except for evidence_quotes"` would make this behavior deterministic rather than emergent.
