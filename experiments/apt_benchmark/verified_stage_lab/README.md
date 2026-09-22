# Verified operations and the limits of earlier context

**Completed development experiment, September 22, 2026. Independent software/calculation audit: PASS for all 2,304 episodes, 21 fitted models, and 810 metric tables. See the [published report](../results/verified_stage_lab_v1/REPORT.md).**

**Finding:** earlier activity perfectly predicted the next operation when the experiment deliberately made them match. A simple rule did exactly as well. When prior and current operations were fully crossed, the contextual model achieved only 25% four-outcome accuracy on successful requests. This does not establish a robust APT detector or a unique benefit from machine learning.

The [literature review](LITERATURE_SCOPE.md) documents direct prior art for using preceding activity and reproducible testbeds. Its proposed design requirements are prospective. The realized experiment below is narrower: it executes harmless application operations and tests workflow dependence. It does **not** execute separate legitimate administration and unauthorized attack campaigns. Opposite authorization labels are counterfactual interpretations of identical transactions, not another measured benign-versus-attack dataset.

## In simple language

We taught a model in an environment where the previous action was a strong clue to the next action. It learned that relationship. It failed when the next action changed. Checking more history helped only while the assumed relationship held; the result does not show that history identified what was actually happening independently of that relationship.

The positive engineering result is a completed fresh collection of real process-to-process requests with independently checkable application outcomes. The scientific result is a limitation: the tested context method learned the deliberately supplied workflow correspondence. There is no demonstrated solution here to distinguishing malicious movement from theft or ordinary administration.

## What actually ran

Three local Windows worker processes performed **2,304 current transactions plus 2,304 preceding transactions**, totaling 4,608 loopback RPCs. Each of 48 randomized blocks crossed four prior-operation requests, four current-operation requests, and three outcome modes. Independent artifact checks establish whether a fixed remote hash computation completed and whether the receiver persisted a complete generated object with the expected bytes and SHA256.

**The transfer label means complete object persistence. Every RPC transmits a dummy buffer, including hash-only and denied requests.** Failed transfer attempts may leave partial files. A negative completed-transfer label therefore does not mean zero transmitted bytes or zero exposure. A positive label does not establish unauthorized theft. The remote-computation label does not establish compromise or malicious lateral movement.

The fixed partitions used 24 fitting blocks, eight calibration blocks, and 16 test blocks. Models fitted only the 288 linked fitting transactions. Calibration predictions were saved without selecting thresholds or model settings. Seven LightGBM feature views across three seeds produced 21 fits, with no hyperparameter search. All three seeds produced identical arm metrics on the same collection; they are not independent scientific replications.

| Test population | All transactions | Successful status-200 transactions | Interpretation |
|---|---:|---:|---|
| Linked | 192 | 64 | Prior and current requests match deliberately |
| Crossed | 576 | 192 | Prior and current requests deliberately differ |
| Full factorial | 768 | 256 | Union of both groups; prior/current requests are independent by construction |

These populations overlap: the full-factorial row is not an additional sample. All three worker processes use the same software and operating system. Their role labels describe logical metadata, not independently managed enterprise hosts.

## Primary results

Four-outcome macro-F1 averages the F1 of neither, remote computation only, complete object persistence only, and both. The current baseline already contains prior-record counts and availability controls; it is **not a flow-only baseline**.

| Population | Current + coverage: all macro-F1 | Full context: all macro-F1 | Current + coverage: status-200 macro-F1 | Full context: status-200 macro-F1 | Simple rule: status-200 macro-F1 |
|---|---:|---:|---:|---:|---:|
| Linked | 0.7654 | 1.0000 | 0.7654 | 1.0000 | 1.0000 |
| Crossed | 0.3166 | 0.2222 | 0.0944 | 0.0000 | 0.0000 |
| Full factorial | 0.4288 | 0.4167 | 0.2621 | 0.2500 | 0.2500 |

Full context improved linked macro-F1 by **23.46 percentage points**, but reduced full-factorial macro-F1 by **1.21 percentage points**. The direct rule and full contextual model made identical hard outcome predictions in the clean condition. Their score rankings need not be identical; for example, crossed transfer AP differs despite identical predicted classes.

The successful-request view matters. The full contextual model had 75% accuracy on all 768 factorial transactions, but only **25% on the 256 successful requests**. Of the full test set, 75% have the completed outcome “Neither,” including failed transactions. The majority predictor also attained 75% overall accuracy while never detecting a completed operation.

On the successful full-factorial population, contextual remote and transfer output precision, recall, F1, AP, and ROC AUC were all **0.5**. Each output had 64 true positives, 64 false positives, and 64 false negatives. Its four-outcome confusion matrix had 16 observations in every cell. This is consistent with predicting the previous operation in a balanced design where previous and current operations are independent.

The linked result is therefore a controlled demonstration of usable correspondence, alongside direct evidence of its failure when that correspondence breaks. It is not evidence that a new model understands adversary intent.

## Missing, delayed, and changed role observations

Models fitted clean observations only. These are fixed observation interventions on the same transactions, not new physical executions or independently sampled deployments.

| Full-context condition | Linked all macro-F1 | Crossed all macro-F1 | Full-factorial all macro-F1 | Full-factorial status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Clean | 1.0000 | 0.2222 | 0.4167 | 0.2500 |
| Remove prior remote-job records | 0.4035 | 0.2749 | 0.3070 | 0.1667 |
| Remove prior file-write records | 0.4035 | 0.2749 | 0.3070 | 0.1667 |
| Add 50 ms to prior arrival time | 0.2143 | 0.2145 | 0.2144 | 0.1003 |
| Permute role metadata | 1.0000 | 0.2222 | 0.4167 | 0.2500 |

Removing either operation channel damaged linked performance. The delay intervention largely removed usable earlier evidence and produced low macro-F1. The small crossed increase under channel removal is not a general improvement: that population deliberately opposes the learned history relationship.

Role permutation made no difference for the full contextual model in this collection. Current plus history also matched current plus roles plus history in the clean condition. These observations show no added clean benefit from role metadata here; they do not establish robustness to real role or domain shifts. The timing diagnostic likewise matched the contextual model's clean outcomes and is reported separately from the six main non-timing arms.

## Hidden authorization is not observable ground truth

Every completed-operation observation was assigned two opposite hidden-policy interpretations while keeping its technical vector and prediction identical. This necessarily yields accuracy and ROC AUC of **0.5**. There were 48 underlying completed-operation observations in linked test, 144 in crossed test, and 192 in their union. Copying their interpretations does not create more executions.

This is an identifiability check: an algorithm cannot recover a policy distinction that is absent from its observations. It is not a measured maliciousness benchmark and does not demonstrate failure or success on actual approved uploads versus theft.

## What this establishes, and the remaining research question

This completed experiment establishes that the collection and verification pipeline can support a controlled test, that deliberately predictive history can be learned, and that this tested relationship fails under the declared mismatch/full-factorial conditions. Generic context fusion remains established prior art. The results do not justify a novel, effective operational APT-method claim.

A useful next confirmation would expose independently collected evidence of the **current** action by a declared decision deadline, while adding realistic, separately executed administrative actions and approved transfers. Operation recognition and authorization should be separate targets. Hold out whole workflow families and compare a direct evidence rule against learned models using the same observations. That is future work, not a result of this run.

## Reproducibility and evidence

- [Frozen design](DESIGN.md) and [protocol](protocol.json).
- [Complete report](../results/verified_stage_lab_v1/REPORT.md), [all aggregate and per-seed metrics](../results/verified_stage_lab_v1/EVIDENCE.json), and [compact summary](../results/verified_stage_lab_v1/SUMMARY.json).
- [Independent audit](../results/verified_stage_lab_v1/AUDIT.json) checks raw outcome artifacts, prepared features, saved predictions, and reported metrics; it is a separately implemented software audit, not human adjudication or peer review.
- [Public file manifest](../results/verified_stage_lab_v1/PUBLICATION.json) binds the published aggregate files.
- [Final execution receipt](RUN_RECEIPT.json) records the scientific freeze, 23 passing collector/audit tests, and file bindings.
- [Separate inference replay](INFERENCE_REPLAY.json) reproduced all 336 saved probability arrays from all 21 fitted models exactly, with maximum difference 0.0. The [replay script](replay_saved_models.py) preserves the actual local repository/data paths used; change those paths and use a fresh output when reproducing elsewhere. The repeated prediction rows are not additional observations.

Collection took 255.93 seconds; fitting and predictions took 15.46 seconds locally. These are separate elapsed measurements, not a GPU speed comparison. No AWS compute ran; the attempted connection and local execution are documented in [AWS_STATUS.md](AWS_STATUS.md). Python 3.11.9, LightGBM 4.6.0, NumPy 2.2.6, scikit-learn 1.7.2, and joblib 1.6.0 are recorded in the run receipt. Raw observations, worker artifacts, probabilities, and models remain private; public files contain metrics and hashes.

### Run a fresh collection and evaluation

Install [requirements.txt](requirements.txt) in Python 3.11 and run from the repository root. Choose new empty directories for each command. The frozen protocol verifies the scientific source bytes before preparation and fitting; do not overwrite the completed evidence.

```text
python -m experiments.apt_benchmark.verified_stage_lab.collector --output <new-collection> --seed 20260922 --blocks 48 --reps 1
python -m experiments.apt_benchmark.verified_stage_lab.run prepare --protocol experiments/apt_benchmark/verified_stage_lab/protocol.json --collection <new-collection> --output <new-prepared>
python -m experiments.apt_benchmark.verified_stage_lab.run fit --protocol experiments/apt_benchmark/verified_stage_lab/protocol.json --prepared <new-prepared> --output <new-run>
python -m experiments.apt_benchmark.verified_stage_lab.audit --collection <new-collection> --protocol experiments/apt_benchmark/verified_stage_lab/protocol.json --prepared <new-prepared> --run <new-run> --out <new-audit.json>
python -m experiments.apt_benchmark.verified_stage_lab.report --run <new-run> --output <new-public-results> --audit <new-audit.json>
```

Fresh collection times, artifact hashes, and observed delay effects may differ. This reproduces the controlled protocol, not the precise physical timing of the original run. Software checks use `python -m pytest experiments/apt_benchmark/verified_stage_lab/tests_collect.py experiments/apt_benchmark/verified_stage_lab/tests_audit.py`; pytest is a separate test dependency.
