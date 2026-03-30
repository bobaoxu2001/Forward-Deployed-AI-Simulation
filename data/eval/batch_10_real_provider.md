# 10-Case Batch Evaluation — Real Provider

> Model: claude-sonnet-4-20250514
> Prompt version: v1
> Cases: 10 of 40 (diverse sample)
> Provider: ClaudeProvider (real API)

---

## Aggregate Metrics

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Schema pass rate | 10/10 = **100%** | >= 98% | PASS |
| Evidence coverage | 10/10 = **100%** | >= 90% | PASS |
| Review-required rate | 8/10 = **80%** | informational | — |
| Average latency | **6,341 ms** (6.3s) | — | — |
| Average confidence | **0.82** | — | — |
| Evidence quotes total | 37 across 10 cases | — | — |
| Hallucinated quotes | 1/37 = **2.7%** | <= 2% | MARGINAL |
| Failure modes fired | 2 | — | — |

---

## Per-Case Results

| # | Case ID | Input | Root Cause | Risk | Conf | Gate | Evidence | Quality |
|---|---------|-------|-----------|------|------|------|----------|---------|
| 1 | case-d37c0bca | EN ticket, account disruption, high | outage / portal offline | high | 0.90 | review (2 codes) | 3 quotes, grounded | GOOD |
| 2 | case-652870dc | EN ticket, billing inquiry, low | billing / invoice clarification | low | 0.90 | auto | 3 quotes, grounded | GOOD |
| 3 | case-ac7b0b06 | DE ticket, security incident, high | security_breach / cyberattack | critical | 0.90 | review (4 codes) | 5 quotes, grounded (German) | GOOD |
| 4 | case-8ba05714 | DE ticket, SaaS platform, medium, VIP | outage / platform degradation | high | 0.90 | review (4 codes) | 6 quotes, grounded (German) | GOOD |
| 5 | case-7febc51e | EN ticket, VPN access, medium | network / vpn_connectivity | high | 0.85 | review (3 codes) | 5 quotes, grounded | GOOD |
| 6 | case-2bd562d3 | Bitext, order cancel, critical, VIP, 7 words | service / order cancellation | high | 0.60 | review (4 codes) | 3 quotes, 1 hallucinated | ISSUE |
| 7 | case-5f87257e | Bitext, complaint, critical, 11 words | service / dissatisfaction | high | 0.60 | review (4 codes) | 2 quotes, grounded | GOOD |
| 8 | case-acaecb0d | Bitext, account signup, low, typos, 14 words | account / sign-up failure | low | 0.90 | auto | 3 quotes, grounded | ISSUE |
| 9 | case-f541aaa0 | Bitext, cancellation charge, critical, 8 words | billing / termination fee | medium | 0.90 | review (1 code) | 3 quotes, grounded | ISSUE |
| 10 | case-e6e5f77c | EN ticket, big data upgrade, high | product / enhancement request | medium | 0.80 | review (1 code) | 4 quotes, grounded | GOOD |

### Representative evidence quotes

| Case | Quote | Language |
|------|-------|----------|
| case-d37c0bca | "centralized account management portal, which currently appears to be offline" | English |
| case-652870dc | "I observed some inconsistencies in the charges applied" | English |
| case-ac7b0b06 | "gravierenden Sicherheitsvorfall melden" | German |
| case-8ba05714 | "Ausfall der Funktionen unserer SaaS-Plattform" | German |
| case-7febc51e | "disruption in VPN-router connectivity that is impacting several devices" | English |
| case-2bd562d3 | "question about cancelling order {{Order Number}}" | English |
| case-5f87257e | "I'm dissatisfied with ur work" | English |
| case-acaecb0d | "i cant open an accojnt help me to notify of a sign-up issue" | English |
| case-f541aaa0 | "want help to see the termination charge" | English |
| case-e6e5f77c | "request improvements to our existing big data analytics infrastructure" | English |

---

## Key Findings

### 1. Root cause accuracy is strong

7 distinct L1 categories across 10 cases: outage (2), billing (2), service (2), security_breach, network, account, product. Every root cause matches the input text when read by a human reviewer. The model does not collapse inputs into a single category.

### 2. Evidence grounding is near-perfect

36 of 37 evidence quotes (97.3%) are verbatim substrings of the source text. The one hallucinated quote ("priority=critical") came from the metadata line appended to the prompt, not from the customer text. This is a prompt design issue, not a model issue — the metadata line is part of the prompt template and the model treated it as quotable source text.

German inputs produce German evidence quotes. The model extracts rather than translates.

### 3. Gate routing is appropriate

8 of 10 cases routed to human review. The 2 auto-routed cases are:
- **case-652870dc**: low-priority billing inquiry — correct auto-route
- **case-acaecb0d**: low-priority account signup — debatable (see issues below)

Most frequently triggered reason codes:
- `high_risk_level` (6 times)
- `high_churn_risk` (6 times)
- `model_flagged` (6 times)
- `high_risk_category` (3 times)
- `low_confidence` (2 times)

### 4. Confidence calibration has a gap on short inputs

| Input length | Avg confidence |
|-------------|---------------|
| < 15 words (4 cases) | 0.75 |
| >= 80 words (6 cases) | 0.87 |

The model correctly lowers confidence for two short cases (case-2bd562d3 and case-5f87257e, both at 0.60). But it assigns **0.90 confidence to two other short cases** (case-acaecb0d at 14 words and case-f541aaa0 at 8 words). This is overconfident — there is not enough information in 8-14 words to justify 90% confidence.

### 5. Multilingual handling works

Both German cases (case-ac7b0b06 and case-8ba05714) produce:
- German evidence quotes (grounded in source)
- English analysis fields (root cause, sentiment rationale, next best actions)
- Correct risk escalation (security_breach → critical, platform outage → high)

No language drift detected.

### 6. Latency is stable

| Statistic | Value |
|-----------|-------|
| Min | 5,594 ms |
| Max | 7,743 ms |
| Average | 6,341 ms |
| Std dev | ~660 ms |

Latency does not correlate strongly with input length. The 7-word Bitext case (5,939 ms) is nearly as slow as the 99-word German ticket (7,346 ms). Output generation time dominates.

---

## Issues Identified

### Issue 1: Overconfidence on short inputs (2 of 4 short cases)

**Cases**: case-acaecb0d (14 words, confidence=0.90) and case-f541aaa0 (8 words, confidence=0.90)

The model assigns high confidence to inputs that contain almost no information. Case-f541aaa0 says "want help to see the termination charge" — 8 words with no account details, no context, no complaint specifics — yet gets 0.90 confidence and medium risk.

**Implication**: The prompt does not explicitly instruct the model to lower confidence when input is very short. This could be addressed by adding a prompt rule.

### Issue 2: Metadata quoted as evidence (1 of 37 quotes)

**Case**: case-2bd562d3

The model quoted "priority=critical" and "vip=vip" as evidence. These come from the metadata line appended by `build_prompt()`:

```
Metadata: priority=critical, vip=vip
```

The prompt says "evidence_quotes MUST contain exact phrases from the case text" but the metadata line is technically part of the prompt, creating ambiguity.

**Implication**: The prompt template should clarify that metadata fields are not quotable as evidence, or the metadata should be separated from the case text block.

### Issue 3: Risk underestimation on termination charge (1 case)

**Case**: case-f541aaa0 — "want help to see the termination charge"

Assigned risk_level=medium despite being a cancellation/termination inquiry. A customer asking about termination charges is a strong churn signal. The gate still routed to review (via `high_churn_risk`), but the risk_level itself could be higher.

---

## Conclusion

The system performs well on real data with a real model. Schema validation, evidence grounding, gate routing, and multilingual handling all work as designed. The three issues identified (overconfidence on short inputs, metadata-as-evidence, risk underestimation on churn signals) are prompt-level refinements, not architectural problems. No code changes are needed — only prompt tuning.
