# Choosing Cyberattack Alert Thresholds from Normal Activity

**Status: complete, independently audited, and AWS verified stopped.**

## Plain-language finding

The fixed normal-calibrated method did not pass all six development cases. The failed cases are reported below; the gates were not changed.

A graph model learns how normal computer activity is connected. We then use a separate normal graph to decide how unusual activity must look before raising an alert. The attack labels are used only to measure the final results; they do not choose these thresholds.

## All six measured results

Every row must meet both gates. Averaging runs cannot rescue a failure.

| Dataset | Seed | Malicious-node recall | Benchmark-negative FPR | Precision | F1 | AUROC | AP | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| THEIA | 0 | 99.996% | 2.723% | 74.432% | 0.8534 | 0.9993 | 0.9894 | FAIL |
| THEIA | 101 | 99.996% | 3.707% | 68.132% | 0.8104 | 0.9991 | 0.9866 | FAIL |
| THEIA | 211 | 99.996% | 3.941% | 66.790% | 0.8009 | 0.9994 | 0.9911 | FAIL |
| CADETS | 0 | 0.000% | 0.145% | 0.000% | 0.0000 | 0.3737 | 0.0560 | FAIL |
| CADETS | 101 | 0.000% | 0.160% | 0.000% | 0.0000 | 0.3744 | 0.0560 | FAIL |
| CADETS | 211 | 0.000% | 0.256% | 0.000% | 0.0000 | 0.3724 | 0.0559 | FAIL |

FPR means the fraction of benchmark-negative rows alerted. AP means average precision. Full confusion counts, thresholds, calibration ties and individual receipts appear in [SUMMARY.json](SUMMARY.json) and [RESULTS.json](RESULTS.json).

## Dataset and unit of measurement

We used the MAGIC authors' prepared DARPA Transparent Computing E3 CADETS and THEIA provenance graphs. A node is a represented computer entity and an edge records a relationship. Counts below are prepared graph rows; they are not verified independent entities or campaigns.

| Dataset | Fitting rows | Separate normal calibration rows | Test rows | Annotated malicious test rows |
|---|---:|---:|---:|---:|
| THEIA | 890,093 | 389,106 | 344,767 | 25,319 |
| CADETS | 1,024,309 | 245,553 | 357,173 | 12,846 |

Each dataset reuses these same prepared partitions across its three fresh training runs. The local conversion preserves original row alignment; missing UUID/time mappings prevent independent campaign or detection-delay claims.

## What was fixed before evaluation

- Two datasets, three runs each (seeds 0, 101 and 211), fresh models and 50 epochs. Prepared train0–2 fit the model and reference bank; train3 sets the threshold; test0 measures the outcome.
- Three fitting graphs give 150 optimizer updates, compared with 200 in the earlier four-graph reproduction. Differences cannot be attributed solely to threshold selection.
- Full fit-bank mean/standard deviation; k=10 for THEIA and k=200 for CADETS. Exact duplicate compression retains every reference occurrence through integer counts; it is an engineering optimization, not a new detector.
- The threshold is the conservative 1% calibration-tail order statistic, with alerts only for scores strictly greater than it. Raw mean neighbor distance is used consistently for calibration and test; no attack-label-selected threshold or author distance-normalizer is used.
- All six normal fits and thresholds were frozen together before any test array was loaded. [GLOBAL_CALIBRATION_FREEZE.json](GLOBAL_CALIBRATION_FREEZE.json) records that boundary.

## Conclusion and limits

Close this fixed six-case experiment as NO-GO for the declared practical-readiness gate. The measured result does not establish that graph models or future checker methods are impossible. It shows that this model, split and fixed normal-calibration rule did not satisfy every required case.

The 1% target describes calibration, not a distribution-free guarantee for later activity. Calibration rows are dependent, the source graphs are assumed filtered benign, and distribution shift remains possible. Calibration is separate from fitting but is not independent normal validation or proof of campaign independence.

These test graphs were previously exposed during development. Each dataset has only one supplied test graph, and prepared rows are not verified independent entities or campaigns. Benchmark-negative rows lack supplied malicious annotations; they are not independently verified innocent. Original UUID/time mappings are absent, and type vocabulary dimensions used training and test types upstream. This study does not establish actor attribution, attack-stage detection, real outage robustness or external generalization.

The original source's masking-target aliasing and absent normalization were retained. Its random-seed helper does not explicitly seed DGL negative sampling; residual randomness remains. Three seeded runs therefore do not isolate initialization alone or establish deterministic retraining. The qualified runtime also differs from the historical author environment.

## Evidence and operational closeout

[INDEPENDENT_AUDIT.json](INDEPENDENT_AUDIT.json) checks saved evidence, fixed calibration rules, metrics/gates, source/checkpoint identities and sampled full-reference distances. The auditor does not retrain models, rerun neural embeddings or verify every distance query. Raw node arrays, weights, logs and infrastructure identifiers remain private; public source receipts and the [artifact manifest](ARTIFACT_MANIFEST.json) bind the published evidence.

The calibrated attempt's estimated compute cost is **$0.473**. Combined compute for all four MAGIC attempts is **$0.884**. The host is verified stopped after each of the four attempts. These estimates run from start request to observed shutdown and exclude storage, transfer, taxes and other resources; they are not invoices. The shared incidental allowance is counted once in [AWS_CLOSEOUT.json](AWS_CLOSEOUT.json).

## Research context

[MAGIC (Jia et al., 2024)](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian) supplies the published model. [PIDSMaker](https://ubc-provenance.github.io/PIDSMaker/features/instability/) already measures retraining instability, and [Faiss](https://github.com/facebookresearch/faiss/blob/v1.7.4/faiss/IndexIVFFlat.cpp#L336) already implements duplicate-aware search. Normal-only calibration and this combination of prerequisites do not establish novelty.

This report closes the fixed calibrated-baseline comparison. The earlier negative stability family remains closed; this result does not change its gates or complete all three original praxis tracks.

## Why a different cutoff alone cannot fix every failure

The following saved score sets have AUROC below the necessary bound of 0.49: **cadets/seed_0, cadets/seed_101, cadets/seed_211**. No threshold in the registered direction (higher means more anomalous) can meet both the 50% recall and 2% false-positive gates on those score sets.

This is an analytical consequence of the measured ranking, not a threshold search: every alerted positive outranks every unalerted negative, so AUROC must be at least recall multiplied by (1 minus false-positive rate). A qualifying operating point would therefore require AUROC of at least 0.50 times 0.98 = 0.49. Ties elsewhere cannot reduce that contribution.

The result applies to these fitted models and saved scores. It does not rule out better representations or other methods. The three-graph design changed fitting data, reference data, standardization and optimizer-update count relative to the four-graph reproduction; the difference cannot be attributed solely to threshold selection. A future checker proposal must address the observed model/score failure rather than assume cutoff retuning will recover the required performance.

## Novelty review

The [current primary-source novelty assessment](../../../docs/MAGIC_CALIBRATION_NOVELTY_BOUNDARY_20260920.md) includes recent work on benign-only threshold selection and stable false-positive-rate meanings across security-model releases. The present experiment tests a practical baseline; a distinct checker improvement remains a separate, unconfirmed research contribution.
