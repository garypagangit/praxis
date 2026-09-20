# Comparing models for malicious behavior, attack stages and earlier warning

Research environment created September20,2026. This branch builds a fair way to discover a useful praxis contribution. A high score on an emulation, or changing the name of a model, does not establish a new contribution.

**Completed missing/delayed-log experiments:** [read the plain-language results](results/robustness_v1/SUMMARY.md). Three experiments, two datasets, sixteen fitted models and 272 audited condition/model/seed results are complete. CasinoLimit shows improved F1 from missing-record training under random loss, but losing command-record types can worsen two targets. Broad reliability and novelty remain unestablished. [Full comparisons](results/robustness_v1/comparison/COMPARISONS.md) and [recent literature](docs/ROBUSTNESS_LITERATURE.md) are available.

**S-DAPT-2026 added:** [source review and proposed evaluations](sdapt2026/README.md), [machine-readable plan](sdapt2026/EVALUATION_PLAN.json), and an unsent source request are prepared. Its January preprint was withdrawn; a later SSRN posting exists, but correction status, raw artifact and license remain unqualified. It has not been fitted or counted as an evaluation-ready dataset.

**Earlier completed pilot:** [first real-data comparison and stage scores](results/pilot_v1/REPORT.md), four binary models plus a separate 12-label step classifier, and 1,768,861 source lines across eight runs. The current environment has 88 passing qualification tests. The development runs used CPU; AWS authentication was verified and the existing GPU host remained stopped. See [full machine-readable dataset catalog](DATASET_CATALOG.json).

An [independent calculation audit](docs/PILOT_AUDIT.md) verified the pilot's metrics and provenance. A separate fixed-model check on 48,838 additional author-rule-nonmatch lines flagged 0.860% with logistic regression, 12.267% with random forest and 8.940% with gradient boosting. These are additional covered files from the same two test runs; no thresholds or models were refitted. Unknown-clock lines were excluded, and the rule-nonmatch labels do not establish independently verified benignness. See [supplemental counts and receipts](results/pilot_v1/background_check_v1.json).

## The three questions

1. **Detection:** Is the observed behavior malicious?
2. **Stage identification:** Which source-documented attack step is occurring?
3. **Early warning:** Does the system raise a useful warning before a documented later harmful action, within a fixed false-alert budget?

APT-inspired emulations support behavior tests. They do not establish attribution to a real bad actor.

## Core data tracks

| Dataset | Role | Readiness |
|---|---|---|
| AIT-LDSv2.1 | Primary enterprise-log detection/step pilot; eight held-out-run units, simulated normal users | Exact source/label-pair acquisition and CPU runner implemented. See results for completion. Data captured2022;2026 packaging is not a new capture. |
| cAPTure, Computer Networks2026 | Conditional network-packet and early-warning replication | Two reduced tables acquired, about1.59GB and2.57million packets. Qualification implemented; causal/reduction provenance remains unresolved. Not fitted in this milestone. |
| CasinoLimit, RAID2025 | Completed technique robustness across execution instances | All114 executions adapted;3,758,674 retained events and8,240 eligible targets. Three target techniques fitted and audited. One challenge, no realistic benign-user baseline. |
| S-DAPT-2026 | Conditional synthetic alert/campaign stress tests | Candidate plan prepared. January paper withdrawn; later preprint correction status, raw files and license need qualification. No fitting. |

AIT-ADS is another observation view of AIT-LDS, not a fourth independent dataset. CAM-LDS, Windows-APT2025, CICAPT-IIoT2024, DEDALE and other alternatives are compared in the two source-backed reviews:

- [Endpoint/APT dataset review](docs/DATASETS_APT_REVIEW.md)
- [Network/multistage dataset review](docs/DATASETS_NETWORK_REVIEW.md)
- [Design and closest literature](docs/BENCHMARK_DESIGN_REVIEW.md)
- [Model types, techniques and implementation status](MODEL_MATRIX.json)

## First runnable comparison

The [frozen pilot protocol](protocol.json) fits on four January AIT runs, uses one later January run for development and one for calibration, then tests on two February runs. All models receive the same normalized source text represented as128 fixed hashed features. Target fields, annotation rules, timestamps and split identifiers never enter the feature builder. Recognized timestamp/address/ID patterns are masked; residual lexical template shortcuts remain a stated limitation.

Implemented: prior-only reference, logistic regression, random forest and histogram gradient boosting, plus a separate multilabel logistic stage classifier. GNNs, temporal Transformers and Qwen are explicitly **planned**, with qualification gates in the model matrix. No GPU job is needed for this CPU milestone.

The pilot uses original log lines in paired, author-annotated intranet files. Missing lines in those positive-label files mean normal under the author's documented convention. Logs without a matching qualified annotation file are unknown, not automatically normal. This selected-source evaluation does not measure complete enterprise sensor coverage. Attacker scripts and label files are never executed.

## Scores and how to interpret them

- Detection: precision, recall, F1, ROC-AUC from continuous scores, average precision (PR metric), balanced accuracy, MCC and confusion counts.
- Operating point: fixed0.5 and a threshold chosen on calibration data for at most1% observed event false positives. Actual test FPR is reported; this is not a population guarantee or a host-hour alarm rate.
- Stages: each binary model's detection of source-labeled steps, plus a distinct multilabel stage-identification table. Source labels overlap and are not forced into a universal chronological order.
- Generalization: both held-out runs shown individually and equally weighted, alongside pooled scores. Two runs do not justify confident population intervals.
- Early-warning library: arrival-time guards, missed/censored episodes, detection delay and before-impact logic are implemented and tested. Real before-impact scoring is withheld until onset, impact, feature availability and monitored benign exposure are qualified. No delay score is invented from a completed-flow or retrospective label.
- Cost: local fit and batch-score seconds. These are not deployed online latency measurements.

## Reproduce locally

Python3.11. A dedicated environment was created at `C:/w/apt_benchmark_env_20260920`; exact installed dependencies are recorded in `requirements.lock.txt` when packaging completes. Raw data, models and row-level predictions stay outside Git.

```powershell
python -m venv C:/w/apt_benchmark_env_20260920
& C:/w/apt_benchmark_env_20260920/Scripts/python.exe -m pip install -r experiments/apt_benchmark/requirements.lock.txt
& C:/w/apt_benchmark_env_20260920/Scripts/python.exe -m unittest discover -s experiments/apt_benchmark/tests -v
& C:/w/apt_benchmark_env_20260920/Scripts/python.exe -m experiments.apt_benchmark.acquire_ait --output C:/w/apt_benchmark_data_20260920/ait/partial_lds
& C:/w/apt_benchmark_env_20260920/Scripts/python.exe -m experiments.apt_benchmark.run_pilot --data C:/w/apt_benchmark_data_20260920/ait/partial_lds --output C:/w/apt_benchmark_data_20260920/pilot_new
```

Optional supplemental background qualification uses a new immutable output:

```powershell
& C:/w/apt_benchmark_env_20260920/Scripts/python.exe -m experiments.apt_benchmark.acquire_background --source-root C:/w/apt_benchmark_data_20260920/ait/partial_lds --output C:/w/apt_benchmark_data_20260920/ait/background_new
& C:/w/apt_benchmark_env_20260920/Scripts/python.exe -m experiments.apt_benchmark.score_background --expansion C:/w/apt_benchmark_data_20260920/ait/background_new --pilot C:/w/apt_benchmark_data_20260920/pilot_new --output C:/w/apt_benchmark_data_20260920/background_new.json
```

The AIT acquirer uses bounded byte ranges, respects rate limits, verifies selected ZIP members by CRC and SHA256, and preserves original line numbering. It records the publisher's full-archive checksum without claiming to have verified an archive it did not download. AIT-LDS is CC-BY-NC-SA4.0: preserve attribution and its noncommercial/share-alike terms. The cAPTure data license has not been verified; raw data is not redistributed.

## Praxis direction

The [praxis decision memo](docs/PRAXIS_DECISION.md) explains the observed weakness: source-step identification of privilege escalation has 73.958% F1 even though overall binary detection exceeds 99.9% F1.

The [next-experiment decision](docs/NEXT_EXPERIMENT.md) now prioritizes source-label scope and event/context representation: a targeted error review found opposite-labeled events with identical normalized inputs. Qualification and stronger simple inputs precede GPU architecture comparisons.

**Candidate:** Can a detector preserve earlier attack-stage warnings when a telemetry source arrives late or disappears, without increasing analyst false alerts?

Build a precise arrival-aware memory or evidence-handling mechanism only after simple baselines and prefix replay are qualified. Compare ordinary updates, lateness buffering, missingness indicators and dropout training before claiming value from a new mechanism. Measure clean operation as well as held-out outages/delay bursts. This is a candidate question, not a novelty or positive-result claim. cAPTure already studies latency/FPR, and recent PIDS frameworks already compare many architectures; a leaderboard alone is insufficient.

The completed robustness suite narrows the next gate: compare source-type-aware training and evidence handling against random dropout, with clean-performance and alert-burden tradeoffs preserved. Qualify independent CAM-LDS scenarios before confirmation. The registered S-DAPT candidate can supply a separate synthetic alert-level check only after its source and shortcut controls pass. Development outcomes cannot be reused as untouched confirmation.
