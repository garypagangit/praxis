# Can evidence checks make automated alert closure safer and useful?

**September 20, 2026: built and started; no positive cybersecurity-performance result yet.**

This implements the detailed **Certified Suppression Gate, G0–G5** proposal in the attachment. Its earlier graph-ablation proposal remains historical context. Branch `cert-gate` is separate from existing `APT-final` experiments.

## Problem and hypothesis in plain language

Analysts spend time investigating harmless alerts. Automation could close some, but closing a real attack is dangerous. We want to test whether checking supporting evidence removes useful amounts of harmless work while limiting the risk of hiding attacks.

The requested limit is **at most 1% of actual attack alerts suppressed, with 95% confidence over calibration samples**, for a frozen scoring rule under documented sampling assumptions. It does not promise that every future batch or attacker-modified stream stays below 1%.

## Built and executed

| Component | Actual status |
|---|---|
| Protocol | Original proposal preserved; corrected release scope recorded before efficacy work. |
| Real-data audit | SecAlertBench acquired and audited: **8,322 alerts; 2,496 Attack and 5,826 Non-Attack**. SIABench artifacts and CORTEX access claim also checked. |
| Evidence gate | Source, trusted severity/rule, incident-context and schema checks implemented and exercised on fixtures. |
| Calibration | Standard binomial order-statistic method implemented; **40,000 independent synthetic calibration sets** run, plus four analytical keep-all settings. |
| Scorers | SVM, pinned-revision Qwen JSON adapter and two-score fusion built. SVM/fusion fitted only on tiny artificial fixtures. **No real-data fitting/scoring or Qwen inference.** |
| Offline replay | Completed on **400 artificial calibration records and 200 artificial test records**, with keep-all, marginal formula, PAC score-only and PAC-plus-predicates arms. Software evidence only. |
| Human review | Final blinded 50-alert form and grading tool prepared. **No reviewer, agreement or approval recorded.** |
| AWS | No GPU needed or launched for this stage. |

**All 49 final tests pass.** They cover sample-size limits, ties, certificate consistency, invalid inputs, evidence tampering, missing context, review blinding, score orientation, label leakage, split separation and reviewer-response validation. The [test receipt](../results/verification_20260920/TEST_RECEIPT.json) records the count, command, source hashes and environment. Qwen's loading/inference path remains untested.

## First real-data finding

**0 of 8,322 released SecAlertBench records meet all four predicates.** Required identity/time fields, trusted severity, full raw-event joins and incident context are absent or unsupported. The gate retains everything. This is a **data-contract feasibility result**, not successful operational certification, scorer failure, or demonstrated workload reduction.

The audit found 7,946 content groups after removing labels and randomized addresses/ports, including 376 excess duplicate rows and one mixed-label group. This does not establish independent attack episodes. Research-use terms were not located in the inspected release; human review is pending. [Exact G0 receipt](../results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json).

| Source | Available evidence | Consequence |
|---|---|---|
| SecAlertBench | Full processed corpus; missing full gate evidence and independence information. | Cannot evaluate the complete registered gate from these records alone. |
| SIABench | Actual acquired release: TII 100 attack/50 non-attack scenarios; CIC 5/30. TII count differs from advertised 50/50. Linked TII archive contains JSON, no PCAPs. | Too few attack cases for this target; unique scenarios do not establish independence. |
| CORTEX | Paper located; actual dataset download not located. | No production dataset acquired or evaluated. |
| Regenerated CIC-IDS2017 | Source/reuse terms checked; full capture-to-alert pipeline not built. | Requires valid alert-label joins and independence analysis. Replaying a capture does not create new independent attacks. |

Hashes and primary links: [data access review](DATASET_ACCESS_REVIEW.md), [manifest](../data_manifest/G0_DATASET_RECEIPT.json).

## Calibration results: software qualification only

The 1%/95% target requires **at least 299 independent attack calibration units** for a nontrivial threshold using this method. Smaller samples take keep-all. Three simultaneous separately certified candidates require a confidence allocation; delta/3 raises the zero-exceedance minimum to 408. Alternatively, select a model first and calibrate it once on fresh independent data.

Each nontrivial setting below uses 10,000 independent Uniform(0,1) calibration sets. The population distribution is known, so true risk is exactly computable. These percentages describe certificate failures across calibration draws; they are **not SOC attack miss rates**.

| Attack units per calibration | Observed failure frequency | Exact theoretical probability | 95% simulation interval |
|---|---:|---:|---:|
| 100, 200, 250, 298 | Analytical keep-all; no Monte Carlo frequency | 0% | Not applicable |
| 299 | 5.20% | 4.9536% | 4.7729–5.6534% |
| 500 | 3.89% | 3.9755% | 3.5195–4.2876% |
| 1,000 | 2.95% | 2.8686% | 2.6271–3.3006% |
| 2,000 | 3.74% | 3.8308% | 3.3766–4.1306% |

The observed 5.20% is preserved, not hidden or rerun with a new seed. Its interval includes the exact 4.9536% probability, consistent with finite Monte Carlo noise. Simulation checks software; the guarantee depends on established mathematics and its assumptions. An independent code review reproduced all 40,000 thresholds using a separate full-sort implementation. [Final results](../results/qualification_20260920_v2/RESULTS.json), [independent review](STARTUP_INDEPENDENT_REVIEW.md).

Additional checks demonstrate important limits:

- At true risk 1%, a 200-attack test exceeds 1% empirically with probability **32.33%**. That alone is not a population-certificate failure.
- A deliberately shifted score distribution can make the rule suppress every constructed shifted example. This is a mathematical counterexample, **not a measured LLM attack**.
- Instructions genuinely recorded in an event can pass source/identity checks. Agreement does not prove benign intent or injection resistance.
- Identical benign/attack score distributions prevent a 1% attack-risk requirement from guaranteeing 20% benign-alert suppression.
- With sufficient examples, all-ineligible calibration can yield a negative-infinity effective threshold. Its future risk remains distribution-conditional; it is not the deterministic keep-all fallback.

Two transparent startup corrections are archived: the first qualification receipt mislabeled analytical placeholder lengths as simulated sample counts; v2 corrects metadata with byte-identical simulation arrays. The final review packet also removes derived attack annotations before any human review. [Amendments](../AMENDMENTS.md).

## Novelty and next decision

Generic certified automatic alert closure already appears in [Şahin and Mert's September 2026 paper](https://doi.org/10.3390/electronics15184084); PAC wrappers also predate this proposal. This code implements established machinery. [Literature review](LITERATURE_REVIEW.md).

**The narrower hypothesis is whether supported evidence predicates improve benign-alert suppression at the same risk target, or reduce attack-induced errors at comparable clean utility, beyond a strong score-only risk-controlled baseline.** Keeping more alerts, substituting Qwen, or beating unprotected closure alone would not establish that contribution. Usefulness and novelty remain unproven.

The next substantive action is to obtain supported raw/context joins and a defensible independence unit, or explicitly narrow/stop the full-gate claim. The [completion kit](HUMAN_REQUIREMENTS.md) supplies an author-request draft, review form, grading command and decision criteria. No external messages were sent.

Once G0 is resolved, freeze model/prompt/revision, fit/selection/calibration/test roles, dependence units, confidence allocation and fair comparators. Then run scorer baselines, utility, and predefined paired attack/drift tests. Real-data replay is currently disabled because that release has not occurred. **No background GPU job is running and no positive real-data result is awaiting collection.**
