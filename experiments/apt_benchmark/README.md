# Comparing models for malicious behavior, attack stages and earlier warning

**Latest completed pilots (September 22): [exfiltration recognition and stage-specialist fusion](exfil_stage_experiments/README.md).** Simple general-plus-specialist averaging raised stage macro-F1 from **0.6749 to 0.6841** and reduced normal false alerts **19.01%**, versus general-model averaging on the same development rows. Lateral any-attack recall fell **0.23 percentage points**. A dedicated exfiltration specialist did not clearly improve exfiltration ranking. Both experiments completed all three seeds; 14 tests and the independent saved-output audit passed. [All results](results/exfil_stage_v1/REPORT.md). These are development findings; attack chronology, independent generalization and novel algorithm claims remain unestablished.

**Current recommended paper: [Improving APT Alert Efficiency: Measured Gains and Lateral-Movement Tradeoffs](lateral_protection_experiment/paper/FINDINGS_PRAXIS.md).** The completed studies show positive improvements with measurable detection costs:

- In the earlier benign-label comparison, adding 992 normal fitting examples while retaining the same 160 attack examples reduced false positives by **96.02%** and raised macro-F1 from **0.4421 to 0.6543**; lateral-flow detection fell from **94.24% to 83.06%**.
- In the new experiment, the candidate produced **33.3% fewer false positives** and raised attack F1 from **0.8770 to 0.9044**, compared with the reference on the **same six feasible seeds**; lateral detection fell from **88.19% to 84.49%**.
- An exploratory comparison on those six seeds found **25.9% fewer false positives** and **0.46 percentage points higher mean lateral recall** for the lateral-sensitive reference than for the ordinary source-normal threshold. Only **two of six seeds improved both measures**, and some other stages declined; the reference also used lateral-labeled selection data while the ordinary threshold used normal selection data only. This is not universal superiority.

All 19 groups and 152 final models in the new experiment completed, with independent calculation audits passing. The **original all-ten-seed screen remains INFEASIBLE**: six selections were feasible and four were not. The findings-led revision adds posthoc interpretation and descriptive comparisons; it changes no fits, thresholds, data, or protocol. SCVIC remains development evidence, and the DEDALE stress tested ordinary controls on one lateral execution. No novel validated algorithm or deployment benefit is established.

[Current Word paper](lateral_protection_experiment/paper/FINDINGS_PRAXIS.docx) | [current PDF](lateral_protection_experiment/paper/FINDINGS_PRAXIS.pdf) | [actual improvements and costs](lateral_protection_experiment/paper/FINDINGS_ACTUALS.md) | [literature gap](lateral_protection_experiment/paper/FINDINGS_LITERATURE_GAP.md) | [original audited result package](results/lateral_protection_v1/REPORT.md). The [prior screen-oriented manuscript](lateral_protection_experiment/paper/PRAXIS.md) and [original eight-page proposal](lateral_protection_praxis/README.md) remain preserved.

This study ran on CPU and passed **40 new implementation and integrity tests**; that count is specific to this study, not a cumulative historical suite count. Its independent-confirmation requirements remain unmet.

**Earlier completed tabular experiment batch:** [final audited tabular APT results and praxis decision](results/tabular_followup_decision_v1/REPORT.md). All 130 model/seed evaluations and ten rare-stage review-policy pairs are complete. The report separates the original foundation-model comparison, stronger controls, the rare-stage checker, and independent Sandworm binary transfer. It includes the benign-label improvement and its lateral-movement detection cost. These are development findings; a novel method and independent attack-stage validation remain unestablished. [Frozen methods and literature](tabular_followup/README.md).

**Previous completed diagnostic:** [combined audit evidence results](results/window_diagnostic_v1/REPORT.md). Across 5,480 fixed CAM-LDS windows and five development families, pooling improves recall at the same review budget from 10.4% to 21.3%, but fails the frozen 40% useful-signal gate and does not beat the simple tool rule. ExtraTrees reaches 19.4%. Fifteen fits and all calculations are independently code-audited; 172 software tests passed for that milestone. **Retire this primary CAM window formulation.** No novel method or fresh confirmation is established.

**Previous completed follow-up:** [structured record-loss results](results/robustness_v2/SUMMARY.md). 30 model/target configurations and 630 audited condition/model results are complete across AIT, CasinoLimit and the CAM-LDS proxy. All five primary screens failed their full criteria. [CAM source qualification](camlds/QUALIFICATION.md) explains why padded window labels do not prove individual-event maliciousness.

Research environment created September20,2026. This branch builds a fair way to discover a useful praxis contribution. A high score on an emulation, or changing the name of a model, does not establish a new contribution.

**Completed missing/delayed-log experiments:** [read the plain-language results](results/robustness_v1/SUMMARY.md). Three experiments, two datasets, sixteen fitted models and 272 audited condition/model/seed results are complete. CasinoLimit shows improved F1 from missing-record training under random loss, but losing command-record types can worsen two targets. Broad reliability and novelty remain unestablished. [Full comparisons](results/robustness_v1/comparison/COMPARISONS.md) and [recent literature](docs/ROBUSTNESS_LITERATURE.md) are available.

**S-DAPT-2026 added:** [source review and proposed evaluations](sdapt2026/README.md), [machine-readable plan](sdapt2026/EVALUATION_PLAN.json), and an unsent source request are prepared. Its January preprint was withdrawn; a later SSRN posting exists, but correction status, raw artifact and license remain unqualified. It has not been fitted or counted as an evaluation-ready dataset.

**Earlier completed pilot:** [first real-data comparison and stage scores](results/pilot_v1/REPORT.md), four binary models plus a separate 12-label step classifier, and 1,768,861 source lines across eight runs. That earlier milestone recorded 252 passing implementation and qualification tests. The development runs used CPU. AWS authentication was previously verified; no AWS compute was started for the latest lateral-protection study. See [full machine-readable dataset catalog](DATASET_CATALOG.json).

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
| CAM-LDS, IJIS2026 | Completed event proxy and five-family window diagnostic | 32 runs; padded global labels, no benign-user workload. Pooling helps but fails useful-signal gate; primary window formulation retired. |
| S-DAPT-2026 | Conditional synthetic alert/campaign stress tests | Candidate plan prepared. January paper withdrawn; later preprint correction status, raw files and license need qualification. No fitting. |
| SCVIC-APT-2021 | Completed few-label, label-noise, and lateral-protection development studies | Author training CSV qualified and feature-deduplicated; 73 predictors, six labels. The lateral-protection primary screen is infeasible in four of ten seeds. Author test set unavailable; no independent-incident or temporal confirmation. |
| Sandworm APT capture, FGCS2026 | Completed independent binary-transfer challenge | 2,091 deduplicated flows, including 37 attacks; ten fits each for TabICL and source-CV-selected boosted trees. No target fitting or calibration. One capture; no Exfiltration stage or independent rare-stage confirmation. |
| DEDALE, ESORICS workshop proceedings2026 | Completed external benign-versus-lateral flow stress test | Sixteen author-labeled flow tables qualified; fixed day17 test has 100,000 sampled benign flows and four lateral flows from one execution. Only ordinary controls were eligible. No target fitting or calibration; insufficient independent executions for protection confirmation. |
| DAPT2020 | Qualified source for possible separately scoped diagnostics | Ten local CSVs audited; only 15 exfiltration rows prevent the proposed all-stage few-shot grid. |
| DSRL-APT-2023 | Synthetic method screening only | Author CSV acquired and pinned; CTGAN derivative of DAPT2020, not an independent real-data validation set. |

AIT-ADS is another observation view of AIT-LDS, not a fourth independent dataset. [DEDALE's acquired flow qualification](lateral_protection_experiment/dedale/QUALIFICATION.md) supersedes its earlier metadata-only status. Windows-APT2025, CICAPT-IIoT2024 and other alternatives are compared in the two source-backed reviews:

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

The [current praxis decision](docs/PRAXIS_DECISION.md) emphasizes measured false-alarm and classification improvements together with their lateral-detection costs. The empirical contribution is a controlled comparison of these choices; the original joint screen remains unchanged. Independent execution-level confirmation remains unavailable in the tested DEDALE subset.

### Historical pilot direction

The original pilot found a source-step identification weakness: privilege escalation has 73.958% F1 even though overall binary detection exceeds 99.9% F1. The recommendations below are preserved as history and do not supersede the completed study above.

The earlier [next-experiment decision](docs/NEXT_EXPERIMENT.md) prioritized source-label scope and event/context representation: a targeted error review found opposite-labeled events with identical normalized inputs. Qualification and stronger simple inputs precede GPU architecture comparisons.

**Candidate:** Can a detector preserve earlier attack-stage warnings when a telemetry source arrives late or disappears, without increasing analyst false alerts?

Build a precise arrival-aware memory or evidence-handling mechanism only after simple baselines and prefix replay are qualified. Compare ordinary updates, lateness buffering, missingness indicators and dropout training before claiming value from a new mechanism. Measure clean operation as well as held-out outages/delay bursts. This is a candidate question, not a novelty or positive-result claim. cAPTure already studies latency/FPR, and recent PIDS frameworks already compare many architectures; a leaderboard alone is insufficient.

The [structured-loss follow-up](results/robustness_v2/SUMMARY.md) and [completed window diagnostic](results/window_diagnostic_v1/REPORT.md) now close the tested augmentation/router and primary CAM window approaches as sufficient praxis solutions. The diagnostic shows a limited pooling benefit, but inadequate useful signal even with complete audit evidence. Do not start an evidence-recovery extension based on it. A new candidate requires independently qualified host/process or evidence-level labels and useful complete-evidence controls. All current CAM outcomes are development evidence. S-DAPT remains conditional on source, data and shortcut qualification.
