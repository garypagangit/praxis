# Few-label APT detection: independent transfer and follow-up evaluation

**Interim report: 2026-09-21T13:06:02.429153+00:00. Full comparison and rare-stage decision remain incomplete.**

## What the completed test tells us

The independent Sandworm transfer test does **not support a useful detector** at
the prespecified argmax operating rule. TabICL improved binary macro-F1 over the
selected tree, but it detected fewer attacks and produced many false alarms.
This is an interpretation of the completed measurements, not a newly invented
success criterion. The previously declared source-calibrated threshold diagnostic
is still pending.

We trained only on SCVIC: 32 labeled examples per class, 192 per seed. We then
tested the frozen models on a different campaign without target training,
calibration, or tuning. The [author dataset](https://zenodo.org/records/16911636)
is associated with a [2026 peer-reviewed paper](https://doi.org/10.1016/j.future.2025.108308).
The evaluation contains 2,091 unique flows: 37 attack and 2,054 normal.

Means across ten source-training seeds, reusing the same target flows:

| Metric | TabICL | Training-CV-selected tree |
|---|---:|---:|
| Attack recall: attacks detected | 44.32% | 76.22% |
| Normal false-positive rate | 28.21% | 40.97% |
| Attack precision: alerts that are attacks | 2.65% | 3.47% |
| Attack F1 | 0.0491 | 0.0661 |
| Binary macro-F1 | 0.4342 | 0.4000 |
| ROC-AUC | 0.7089 | 0.7473 |
| Average precision | 0.0380 | 0.1054 |

TabICL detected an average **16.4 of 37 attack flows**
and produced **579.4 false alarms among 2,054 normal flows**.
The tree detected 28.2 attacks with
841.5 false alarms. TabICL's macro-F1 gain is
+3.42 percentage points, while its attack
recall is 31.89
percentage points lower. This relative score gain is not operational success.

Calling every flow normal would yield 98.23% accuracy and 0.4955 macro-F1 while
detecting zero attacks. This arithmetic reference was added for interpretation
after partial results; it is not a fitted comparison arm or a new success gate.
It illustrates why accuracy and macro-F1 cannot be the whole decision.

All 20 model/seed cells passed an independent provenance and metric audit.
See [the audited aggregate evidence](TRANSFER_SUMMARY.json). Audit PASS means the
records and calculations checked out; it does not mean the scientific hypothesis passed.

## What is still running

Completion counts are a snapshot, not final audited outcomes:

| Work | Completed cells / required | State |
|---|---:|---|
| Original full tree baselines | 30/30 | Previously audited |
| Original full-query TabICL | 0/10 | CPU worker running |
| Original full-query TabPFN | 0/10 | CPU worker running |
| Stronger trees, two label budgets | 45/60 | CPU worker running |
| Independent binary transfer | 20/20 | Audited; operationally unfavorable |
| Rare-stage review policy | 0/10 seed pairs | Waiting for full calibration predictions |

The frozen review policy asks whether combining the two models catches more of
the harder InitialCompromise/DataExfiltration stage without exceeding the review
budget. It must beat both single-model controls, protect the other stages, and
meet the specified per-seed false-alarm limit. It uses 29,929 additional benign
calibration labels, so it is not a 192-total-label system.

The [completion watcher](../../tabular_followup/RUN_STATUS.md) is running. It will
audit the remaining results and publish a final report if all required workers
finish successfully before its 12-hour deadline. It preserves explicit incomplete
or error states otherwise. No AWS resources were started; authentication is expired.

## Praxis decision and limits

**No novel, independently validated improvement is established yet.** The
earlier sampled development result justified this test, but the new independent
result does not confirm useful transfer. The source rare-stage experiment remains
unresolved. A positive development gate alone would still need independent
stage-labeled incidents.

This is one independent campaign with only 37 attack flows. Ten training seeds
are not ten independent incidents. Sandworm's procedure labels differ from SCVIC's
stage labels and contain no exfiltration category. Matching feature names do not
prove identical extractor settings. The test measures binary transfer; it does
not establish early detection, missing-log resilience, or stage identification.
Raw-flow reweighting leads to the same practical conclusion and is documented
in the aggregate evidence; it does not rerun inference on a differently composed batch.

The [literature review](../../tabular_followup/NOVELTY_POSITION.md) documents
direct prior work on tabular foundation models, trees, conformal uncertainty,
few-shot transfer, and rescue paths, including
[Lawall's 2026 author presentation](https://www.dtrsociety.org/wp-content/uploads/library/porto2026/keynotes/CYBERSEC2026_02_002.pdf).
The exact constrained evaluation remains worth finishing; a first-method claim
is unsupported.

## Reproducibility

The complete software suite passed 328 tests in 72.392 seconds. Protocols and
source are frozen before the relevant outcomes; the independent audit verifies
input, code, checkpoint, prediction, and completion hashes. The source-only 1%
threshold diagnostic is predeclared and will use matching source calibration
predictions, without changing target labels or refitting on the target.

Only code, documentation, and aggregate evidence are published. Raw/derived
flow records, model checkpoints, and credentials remain outside Git. Dataset
rights ambiguity and feature/label limits are recorded in the
[qualification](../../tabular_followup/HOLDOUT_QUALIFICATION.md).
