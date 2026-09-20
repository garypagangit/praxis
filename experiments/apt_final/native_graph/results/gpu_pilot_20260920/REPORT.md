# Missing Graph Connections: First APT Detection Pilot

## Decision

**Completed and independently audited; detector readiness was not met.** The alternative datasets support this static development experiment, but the lightweight detectors missed almost all annotated malicious entities at the frozen alert thresholds. The degree-based checker added no useful improvement. This is not evidence that all routing approaches fail, or that the datasets are unusable.

## What we ran

- DARPA TC E3 CADETS and THEIA graphs supplied by the MAGIC authors; 701,940 evaluation-node records and 38,165 malicious annotations across two evaluation graphs.
- Three model seeds per dataset. Train on three author training graphs; calibrate on a separate fourth graph. Training benign status follows the source's filtering assumptions.
- A small GIN reconstruction detector, an MLP using local type/count features, Isolation Forest, node-type rarity, a fixed observed-degree checker, and a confidence selector. This is a custom diagnostic, not a reproduction of published MAGIC performance.
- Remove 0%, 25%, 50%, 75%, or 100% of retained graph relationships. Recompute affected local features for every arm. Two removal seeds yield 54 logged model/scenario evaluations, including six duplicate empty-graph cases; 48 model/input combinations are distinct.
- Fix each detector's alert threshold using a nominal 1% false-positive target on the clean calibration graph, with conservative score ties. No threshold was selected from attack labels.

## Clean-graph results

Percentages below are means over three model seeds. Recall is the fraction of annotated malicious entities flagged. False-positive rate uses unannotated benchmark negatives; those are not exhaustively verified benign records.

| Dataset | GIN recall | Checker recall | Isolation Forest recall | Checker false-positive rate |
|---|---:|---:|---:|---:|
| CADETS | 0.104% | 0.104% | 0.039% | 1.146% |
| THEIA | 0.043% | 0.043% | 1.943% | 1.127% |

THEIA Isolation Forest had mean average precision 0.668, showing useful ordering information in its scores, but detected only 1.94% of malicious annotations at the frozen threshold. Its ranking score does not establish an effective alerting system. Overall accuracy is not treated as success because predicting normal for nearly everything benefits from class imbalance.

## Missing-relationship results

| Dataset | Relationships removed | GIN recall | Checker recall | Checker false-positive rate |
|---|---:|---:|---:|---:|
| CADETS | 0% | 0.104% | 0.104% | 1.146% |
| CADETS | 25% | 0.093% | 0.093% | 0.932% |
| CADETS | 50% | 0.079% | 0.079% | 0.636% |
| CADETS | 75% | 0.052% | 0.052% | 0.294% |
| CADETS | 100% | 0.000% | 0.000% | 0.025% |
| THEIA | 0% | 0.043% | 0.043% | 1.127% |
| THEIA | 25% | 0.034% | 0.034% | 0.847% |
| THEIA | 50% | 0.032% | 0.032% | 0.625% |
| THEIA | 75% | 0.018% | 0.018% | 0.358% |
| THEIA | 100% | 0.000% | 0.000% | 0.001% |

Lower false-positive rates under heavy loss came with lower detection. At complete relationship loss, the neural arms and checker detected no malicious entities. Full metrics, including the stronger simple baselines and confidence selector, are in [SUMMARY.csv](SUMMARY.csv) and [ALL_CONDITIONS.csv](ALL_CONDITIONS.csv).

## Why the next step is the detector

A separately labeled [post-hoc diagnostic](POSTHOC_DIAGNOSTIC.json) of saved predictions found almost no useful complementary detections between MLP and GIN on clean data. Many malicious entities received identical reconstruction scores below the high-error benign tail. This points to a representation/scoring problem worth investigating; it does not isolate its cause. The diagnostic changes no model, threshold, or original result.

Next: reproduce a documented MAGIC-style benign encoder with nearest-neighbor embedding scores, compare it with the current reconstruction score and Isolation Forest, and keep independent benign calibration. Only build a learned checker once candidate detectors show useful complementary detections. Any follow-up on these examined test graphs remains development, under a new protocol and registration. Recover semantic/time information from richer public data for later transfer or delayed-log claims.

## Verification and limits

[50 software tests passed](SOFTWARE_VERIFICATION.json). Both real dataset runs passed actual CPU/CUDA model parity, exact repeated CUDA-output checks, and deterministic backward checks. An independent auditor recomputed saved metrics, calibration margins, routing decisions, removal masks, and corrected/introduced errors, and verified fitted-artifact hashes. [Independent audit](INDEPENDENT_RESULT_AUDIT.json).

The two dataset pipelines took about 303 seconds combined on an NVIDIA A10G, including fitting, evaluation and evidence writing; this is not a measured speedup against CPU. The [operational closeout](AWS_CLOSEOUT.json) records the initial environment-selection failure, successful repaired attempt, verified resource shutdown and an approximately $0.26 combined compute estimate (excluding storage and other charges; not an invoice). No private arrays, weights or credentials are published.

Prepared graphs omit timestamps and UUID mappings, their type IDs differ across datasets, and only one attack-bearing graph per dataset was evaluated. THEIA uses separately fitted models under the same procedure. No campaign confidence interval, frozen-model transfer, five-stage classification, deployment claim, or novelty claim is established.
