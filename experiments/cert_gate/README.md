# Certified suppression gate for SOC alert triage

**Branch: `cert-gate`. Built and started September 20, 2026.** Offline research; no live alert is suppressed.

The program evaluates how much benign-alert workload can be removed while controlling the fraction of actual attacks suppressed. Useful suppression is an empirical question. Statistical risk control, integrity checks and novelty are separate requirements.

Start with the [plain-language results](docs/STARTUP_REPORT.md) and [next human/data actions](docs/HUMAN_REQUIREMENTS.md).

## Evidence from completed startup runs

- [Current status](STATUS.json)
- [G0: 8,322 real records audited; none support every required predicate](results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json)
- [40,000 synthetic calibration draws and analytical fallback checks](results/qualification_20260920_v2/RESULTS.json)
- [End-to-end replay on artificial records](results/replay_fixture_20260920/run/RESULTS.json)
- [Independent results review](docs/STARTUP_INDEPENDENT_REVIEW.md)
- [Literature and novelty](docs/LITERATURE_REVIEW.md), [statistical contract](docs/STATISTICAL_CONTRACT.md)

The first-attempt G0 and qualification folders remain as audit history. Use the linked **v2** receipts and `human_review_v2` packet. No human review has been completed. No real-data performance result is claimed.

The [registration](REGISTRATION.json) currently releases G0 and software qualification. [Amendments](AMENDMENTS.md) explain why the original draft cannot be executed literally. Real-data model reproduction and confirmatory G2-G5 remain gated on actual data support, reviewed labels and a model-specific frozen protocol. No human review, literature reproduction, workload benefit or novelty is asserted by constructing this harness.

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

SVM/fusion tests use artificial examples only. Qwen has not been downloaded or run for this study; its inference path needs qualification after an exact model/runtime is frozen. No published-model reproduction is claimed. [Why G1-G5 remain unreleased](docs/HUMAN_REQUIREMENTS.md).
