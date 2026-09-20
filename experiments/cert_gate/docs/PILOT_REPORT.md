# The workaround produced a positive exploratory benchmark

**September 20, 2026.** We separated score-only triage from the unavailable full evidence gate, registered that change before model fitting, and ran a real SecAlertBench experiment. This keeps the project moving without claiming that the original G0 requirements passed.

## What the experiment shows

The fixed SVM plus calibrated threshold suppressed **1,076 of 1,123 benign test representatives (95.81%)** and **1 of 491 attack representatives (0.20%)**. It retained 490 attack examples for investigation. These are measured offline benchmark outcomes, not live alert closures or a verified population safety certificate.

| Rule on the same 1,614 test representatives | Benign examples suppressed | Attack examples suppressed |
|---|---:|---:|
| Retain every alert | 0/1,123 — 0% | 0/491 — 0% |
| Ordinary SVM decision cutoff | 1,099/1,123 — 97.86% | 3/491 — 0.61% |
| Marginal order-statistic cutoff | 1,094/1,123 — 97.42% | 2/491 — 0.41% |
| PAC-style calibrated cutoff | **1,076/1,123 — 95.81%** | **1/491 — 0.20%** |

The calibrated cutoff retained two additional attack representatives while retaining 23 additional benign representatives compared with the ordinary SVM cutoff. That small paired difference does not establish statistical superiority. The scorer itself had test F1 **97.31%**, attack recall **99.39%**, and false-positive rate **2.14%**. These are our fixed-SVM results on our split, not a reproduction of the published multi-model average.

The registered 10,000 empirical group resamples give a **94.62–96.94%** band for benign suppression and **0–0.64%** for attack suppression under the PAC-style cutoff. These summarize resampling of this observed collection; they are not independent-incident population confidence intervals. Small error counts and unknown dependence remain important.

As a separate secondary denominator, all 1,712 retained test rows give 1,148/1,196 benign alerts suppressed (95.99%) and 1/516 attacks (0.19%). Do not mix those row counts with the primary representative counts.

## What protected the pilot from obvious leakage

- Original source: 8,322 rows. Grouping found 7,913 families after masking valid IPv4 literals **only for grouping**. Original model text remained unchanged.
- All 50 reserved human-review families were excluded: 74 rows. Three mixed-label families, six rows, were also excluded prospectively. Such conflicts need not be labeling errors; exclusion narrows the evaluated population.
- Retained families were assigned by a fixed, label-independent hash: 3,157 fitting, 734 diagnostic-selection, 2,355 calibration and 1,614 test representatives. No seed or model was selected from the results.
- Calibration used 727 attack representatives. The learned model and thresholds were saved before test scoring. The PAC-style threshold was 0.4234546585, allowing two calibration exceedances under the formula.
- Labels and derived attack/kill-chain annotations were excluded from model features. Feature families do not establish independent attacks or eliminate every possible shared template, campaign or rule-type effect.
- The run took about 80 seconds on CPU, with about 620 MiB process peak memory and no fit warnings. Timing is descriptive, not a hardware comparison. No Qwen or AWS compute was used.

[Frozen protocol](../PILOT_PROTOCOL.json), [raw aggregate results](../results/score_only_pilot_20260920/RESULTS.json), [pre-test freeze](../results/score_only_pilot_20260920/CALIBRATION_FREEZE.json), [independent result audit](PILOT_RESULT_AUDIT.md). Raw records, model and individual predictions remain private; their hashes are recorded.

## The packet-capture workaround was also exercised

We acquired two real PCAPNG captures from the published SIABench CIC subset using byte ranges, avoiding full-day downloads. They contain **10,185 packets** in total. The existing scenario labels describe the original Snort analysis; they cannot label every new Suricata alert.

1. **Natural-rule attempt:** Suricata8.0.7 loaded 52,302 ET Open rules; nine file-magic rules were unsupported by this Windows build. Both compact captures produced **zero alerts**. This supplies no natural-alert suppression result. The attempt is preserved.
2. **Explicit instrumentation attempt:** two diagnostic packet rules emitted events solely to test the links to original packets. They do not detect attacks. This exposed a Windows timestamp-formatting defect; the failed attempt was preserved.
3. **Corrected runtime:** a fresh run with process-local `TZ=UTC0` retained the same captures and strict one-microsecond matching tolerance. **4,778/4,784 diagnostic events (99.87%)** matched their original packet fields. One unknown filename and five unsupported IPv6 records were rejected. No guessed timestamp offset was applied.

This establishes that we can acquire captures, replay them and verify most packet references locally. It does not supply an enterprise user identity, complete incident history, independent attack count, or a successful full suppression gate. [Runtime audit](TIER3_RUNTIME_AUDIT.md), [final linkage results](../results/tier3_instrumentation_20260920_v2_utc/RESULTS.json), [feasibility and sources](TIER3_FEASIBILITY.md).

## Which advice was right, and what still needs correction

**Right:** the author email need not hold up a score-only pilot. Gary can conduct the real 50-alert review himself and disclose that it is a single-rater audit. A smaller capture subset can test data-processing feasibility. Those paths are now implemented and exercised.

**Overstated:** completing 50 reviews does not automatically yield the required 45 agreements; a programmatic label join is not independent truth validation; two attack days do not automatically supply all original predicates or 299 independent attack units. A positive result and a publication timeline cannot be promised in advance. Known CICIDS2017 labeling/flow issues make a carefully validated join necessary. [Primary dataset](https://www.unb.ca/cic/datasets/ids-2017.html), [dataset error study](https://intrusion-detection.distrinet-research.be/WTMC2021/).

## Recommendation: continue, with a narrower contribution

**There is now a positive feasibility result worth following up. A wholesale pivot is not required to take the next useful step.** The score-only baseline already performs strongly, so the contribution must be a demonstrable improvement beyond it. Generic certified closure already has [close prior work](https://doi.org/10.3390/electronics15184084).

The next sequence is concrete:

1. Gary completes the [existing blinded review](C:/w/cert_gate_data_20260920/human_review_v2/REVIEW.html), including unable-to-verify outcomes. It was kept out of this pilot.
2. Freeze a harder generalization test, such as holding out rule/template families, before examining its results. Current shared-rule benchmark performance alone does not establish transfer to unfamiliar attacks.
3. For the proposed better checker, register the supported **network-only** N1–N4 contract described in the feasibility memo. Obtain natural alerts and validate alert-level labels against packet/flow evidence; do not count diagnostic events as attacks.
4. Compare the checker with the score-only baseline at comparable benign-alert suppression, using predefined missing-evidence and source-consistent instruction conditions. Preserve all outcomes. Human review, a second suitable source and defensible sampling remain necessary for stronger claims.

The original two-dataset utility hypothesis, attack robustness and novel contribution are still unconfirmed. We have nevertheless moved from software-only checks to an actual positive benchmark and an executed capture-provenance prototype. No external email was sent; the draft remains available if desired.
