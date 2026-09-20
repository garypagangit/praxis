# Certified suppression gate for SOC alert triage

**Branch: `cert-gate`. Built and started September 20, 2026.** Offline research; no live alert is suppressed.

**Final automated continuation: the added checker showed no benefit.** On the harder unseen-rule test, the calibrated full scorer and checker both cleared 1,610/1,696 benign-labeled representatives (94.93%) and 0/412 attack-labeled representatives. Their per-row decisions were identical across all six test settings. One component contains 87.62% of benign examples, so the high aggregate clearance rate is not evidence of broad reliability. [Final report](docs/FINAL_REPORT.md), [all benchmark results](results/final_generalization_20260920/RESULTS.json), [frozen continuation protocol](FINAL_PROTOCOL.json).

**Design correction:** the programmed practical pass rule was unattainable at the observed baselines: it required negative attack error or more than 100% benign clearance. Its `NO_GO` flag therefore cannot establish scientific failure. The separate observation of zero changed decisions remains valid. The original checker requiring independent raw-event evidence was not tested for efficacy. [Detailed correction](docs/FINAL_REPORT.md#post-run-correction-the-practical-pass-rule-had-a-ceiling-problem).

A pinned Qwen bot also completed the 50-case automated review: **10 agreements, 24 disagreements and 16 unusable responses**. Its 20% agreement failed the 45/50 benchmark. See [bot results](results/automated_review_20260920/RESULTS.json), [confusion-table recount](results/automated_review_20260920/RECOUNT.json), and [reusable bot instructions](docs/AUTOMATED_REVIEW.md). This is automated review, not fulfillment of the historical human-review criterion. AWS is verified stopped. The [earlier score-only pilot](docs/PILOT_REPORT.md) and packet-provenance attempts remain as history.

The program evaluates how much benign-alert workload can be removed while controlling the fraction of actual attacks suppressed. Useful suppression is an empirical question. Statistical risk control, integrity checks and novelty are separate requirements.

The [startup report](docs/STARTUP_REPORT.md) records the earlier software-only stage. [Human/data actions](docs/HUMAN_REQUIREMENTS.md) remain relevant to stronger validation.

## Evidence from completed startup runs

- [Current status](STATUS.json)
- [G0: 8,322 real records audited; none support every required predicate](results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json)
- [40,000 synthetic calibration draws and analytical fallback checks](results/qualification_20260920_v2/RESULTS.json)
- [End-to-end replay on artificial records](results/replay_fixture_20260920/run/RESULTS.json)
- [Independent results review](docs/STARTUP_INDEPENDENT_REVIEW.md)
- [Literature and novelty](docs/LITERATURE_REVIEW.md), [statistical contract](docs/STATISTICAL_CONTRACT.md)

The first-attempt G0 and qualification folders remain as audit history. Use the linked **v2** receipts and `human_review_v2` packet. No human review has been completed. The later score-only pilot reports real-data exploratory performance; full-gate efficacy and operational certification remain unproven.

The original [registration](REGISTRATION.json) released G0 and software qualification. The [pilot protocol](PILOT_PROTOCOL.json) released score-only exploration and compact packet-linkage checks; [FINAL_PROTOCOL.json](FINAL_PROTOCOL.json) released the completed automated continuation. [Amendments](AMENDMENTS.md) preserve that sequence. Published-model reproduction and confirmatory G2-G5 remain uncompleted; the original full gate is not declared validated.

## Risk contract

Let `s(x)` be a frozen benignness score and `e(x)` the frozen deterministic eligibility rule. The gate suppresses only if `e(x)` and `s(x)>threshold`. The primary target is `P(suppress | true attack)<=0.01`, with 95% confidence over independent attack-calibration samples under the stated distributional assumptions. The denominator includes all attacks, not just eligible ones. A conservative fallback keeps every alert when nontrivial calibration is unsupported. This is established statistical machinery.

## Data and evidence

Raw downloaded corpora and human-review excerpts stay outside Git. Committed manifests contain exact hashes, acquisition/qualification outcomes and reproduction instructions. The user proposal is user-provided source material. Generated fixtures and simulation outcomes are software evidence and must never be counted as real SOC results.

## Reproduce software checks

Use Python 3.11 and [requirements.txt](requirements.txt). From the repository root, use the direct paths below for the older runners. The new bot modules also support `python -m experiments.cert_gate...` invocation:

```powershell
python -m unittest discover -s experiments/cert_gate/tests -v
python experiments/cert_gate/qualify.py --output experiments/cert_gate/results/my_qualification
python experiments/cert_gate/make_fixture.py --output experiments/cert_gate/results/my_fixture/INPUT.json
python experiments/cert_gate/replay.py --input experiments/cert_gate/results/my_fixture/INPUT.json --output experiments/cert_gate/results/my_fixture/run
```

Output paths must be new; runners preserve attempts. The tested local interpreter is `C:/w/cti_checker_env_20260918/Scripts/python.exe`. The SVM benchmarks and software checks need no GPU; the completed Qwen audit used the existing authorized AWS GPU host. Fixture replay remains explicitly separate from the real-data benchmark. A scope label does not authenticate data provenance.

To repeat G0 against the acquired artifact, use new private/output folders:

```powershell
python experiments/cert_gate/g0_audit.py --source 'C:/w/cert_gate_data_20260920/access_review/SecAlertBench/0x02. Processed SecAlertBench Dataset/secalertbench.json' --private-review-dir 'C:/w/cert_gate_data_20260920/my_new_review' --output experiments/cert_gate/results/my_g0/ELIGIBILITY_AND_REVIEW.json
```

The [manifest](data_manifest/G0_DATASET_RECEIPT.json) pins source commits, hashes and acquisition outcomes. Raw data and human-review excerpts are not redistributed in Git. Obtaining an artifact does not establish its research terms or complete G0.

## Scorer interfaces

`scorers.py` implements character-TFIDF/linear SVM, a Qwen JSON adapter requiring an immutable revision, and learned fusion of two score columns. Higher scores mean more benign. Training requires a declared fitting role; actual split integrity remains the caller's responsibility. Feature serialization excludes labels and derived attack tags.

SVM unit tests use artificial examples; the pilot and final comparison fit fixed SVMs to real fitting representatives. Fusion remains fixture-tested only. The separate [automated reviewer](auto_review.py) ran pinned Qwen3-4B-Instruct-2507 on 50 blinded cases; the older QwenJSONScorer adapter was not used as a benchmark arm. No published-model reproduction is claimed.

## Reproduce the exploratory pilot

Commit the operative files and protocol first; the runner checks their bytes before fitting. Use new output folders and the pinned source/audit:

```powershell
python experiments/cert_gate/exploratory_benchmark.py --source 'C:/w/cert_gate_data_20260920/access_review/SecAlertBench/0x02. Processed SecAlertBench Dataset/secalertbench.json' --protocol experiments/cert_gate/PILOT_PROTOCOL.json --audit experiments/cert_gate/results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json --private-output 'C:/w/cert_gate_data_20260920/my_pilot_repeat' --output experiments/cert_gate/results/my_pilot_repeat
```

Primary and all-row secondary results, resampling bands, timing and private hashes are in [the pilot receipt](results/score_only_pilot_20260920/RESULTS.json). A repeat on the same test data is a reproducibility check, not fresh confirmation.

For packet replay, see [the acquisition memo](docs/TIER3_FEASIBILITY.md), [runtime audit](docs/TIER3_RUNTIME_AUDIT.md), and the exact command/configuration and binary/rule hashes in [the generation freeze](results/tier3_instrumentation_20260920_v2_utc/GENERATION_FREEZE.json). The diagnostic rules exercise packet links and make no attack judgment.

## Reproduce the final comparison

Use fresh output directories and the same pinned source. The runner verifies committed operative bytes, fits four models across two split regimes, freezes all cutoffs, and evaluates eight arms under three conditions:

```powershell
python experiments/cert_gate/generalization_benchmark.py --source 'C:/w/cert_gate_data_20260920/access_review/SecAlertBench/0x02. Processed SecAlertBench Dataset/secalertbench.json' --protocol experiments/cert_gate/FINAL_PROTOCOL.json --audit experiments/cert_gate/results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json --private-output 'C:/w/cert_gate_data_20260920/my_generalization_repeat' --output experiments/cert_gate/results/my_generalization_repeat
```

The final software suite passed **93 tests**. [Verification receipt](results/final_verification_20260920/TEST_RECEIPT.json), [AI-assisted code and saved-results audit](docs/FINAL_SOFTWARE_AUDIT.md). Repeating this observed test does not create independent confirmation.
