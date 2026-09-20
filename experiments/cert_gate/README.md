# Certified suppression gate for SOC alert triage

**Branch: `cert-gate`. Built and started September 20, 2026.** Offline research; no live alert is suppressed.

**Update: a real-data score-only pilot is now complete.** The calibrated cutoff removed 1,076/1,123 benign test representatives (95.81%) and 1/491 attacks (0.20%). A separate packet-provenance prototype also ran. [Current results and next steps](docs/PILOT_REPORT.md), [prospective pilot protocol](PILOT_PROTOCOL.json).

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

The original [registration](REGISTRATION.json) released G0 and software qualification. The new [pilot protocol](PILOT_PROTOCOL.json) releases a fixed exploratory score-only benchmark and compact packet-linkage checks. [Amendments](AMENDMENTS.md) preserve that sequence. Published-model reproduction and confirmatory G2-G5 remain gated; exploratory success is not a pass for those stages.

## Risk contract

Let `s(x)` be a frozen benignness score and `e(x)` the frozen deterministic eligibility rule. The gate suppresses only if `e(x)` and `s(x)>threshold`. The primary target is `P(suppress | true attack)<=0.01`, with 95% confidence over independent attack-calibration samples under the stated distributional assumptions. The denominator includes all attacks, not just eligible ones. A conservative fallback keeps every alert when nontrivial calibration is unsupported. This is established statistical machinery.

## Data and evidence

Raw downloaded corpora and human-review excerpts stay outside Git. Committed manifests contain exact hashes, acquisition/qualification outcomes and reproduction instructions. The user proposal is user-provided source material. Generated fixtures and simulation outcomes are software evidence and must never be counted as real SOC results.

## Reproduce software checks

Use Python 3.11 and [requirements.txt](requirements.txt). From the repository root, use direct script paths; these modules are not packaged for `python -m` invocation:

```powershell
python -m unittest discover -s experiments/cert_gate/tests -v
python experiments/cert_gate/qualify.py --output experiments/cert_gate/results/my_qualification
python experiments/cert_gate/make_fixture.py --output experiments/cert_gate/results/my_fixture/INPUT.json
python experiments/cert_gate/replay.py --input experiments/cert_gate/results/my_fixture/INPUT.json --output experiments/cert_gate/results/my_fixture/run
```

Output paths must be new; runners preserve attempts. The tested local interpreter is `C:/w/cti_checker_env_20260918/Scripts/python.exe`. No GPU is needed. Replay accepts only explicitly declared software fixtures until the real-data protocol is released. A scope label does not authenticate data provenance.

To repeat G0 against the acquired artifact, use new private/output folders:

```powershell
python experiments/cert_gate/g0_audit.py --source 'C:/w/cert_gate_data_20260920/access_review/SecAlertBench/0x02. Processed SecAlertBench Dataset/secalertbench.json' --private-review-dir 'C:/w/cert_gate_data_20260920/my_new_review' --output experiments/cert_gate/results/my_g0/ELIGIBILITY_AND_REVIEW.json
```

The [manifest](data_manifest/G0_DATASET_RECEIPT.json) pins source commits, hashes and acquisition outcomes. Raw data and human-review excerpts are not redistributed in Git. Obtaining an artifact does not establish its research terms or complete G0.

## Scorer interfaces

`scorers.py` implements character-TFIDF/linear SVM, a Qwen JSON adapter requiring an immutable revision, and learned fusion of two score columns. Higher scores mean more benign. Training requires a declared fitting role; actual split integrity remains the caller's responsibility. Feature serialization excludes labels and derived attack tags.

SVM unit tests use artificial examples; the later pilot fits the fixed SVM to real fitting representatives. Fusion remains fixture-tested only. Qwen has not been downloaded or run for this study. No published-model reproduction is claimed.

## Reproduce the exploratory pilot

Commit the operative files and protocol first; the runner checks their bytes before fitting. Use new output folders and the pinned source/audit:

```powershell
python experiments/cert_gate/exploratory_benchmark.py --source 'C:/w/cert_gate_data_20260920/access_review/SecAlertBench/0x02. Processed SecAlertBench Dataset/secalertbench.json' --protocol experiments/cert_gate/PILOT_PROTOCOL.json --audit experiments/cert_gate/results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json --private-output 'C:/w/cert_gate_data_20260920/my_pilot_repeat' --output experiments/cert_gate/results/my_pilot_repeat
```

Primary and all-row secondary results, resampling bands, timing and private hashes are in [the pilot receipt](results/score_only_pilot_20260920/RESULTS.json). A repeat on the same test data is a reproducibility check, not fresh confirmation.

For packet replay, see [the acquisition memo](docs/TIER3_FEASIBILITY.md), [runtime audit](docs/TIER3_RUNTIME_AUDIT.md), and the exact command/configuration and binary/rule hashes in [the generation freeze](results/tier3_instrumentation_20260920_v2_utc/GENERATION_FREEZE.json). The diagnostic rules exercise packet links and make no attack judgment.
