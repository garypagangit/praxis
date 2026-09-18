# Completed CTI evidence package

Start with [DECISION.md](DECISION.md) for the plain-language conclusion and [REPORT.md](REPORT.md) for all results. The complete external experiment failed its preset benefit and added-value criteria. The earlier positive pilot is retained separately.

## Included material

- Frozen protocol, inputs, labels, checker decisions, model revisions, and executable analysis.
- Complete fresh raw outputs, scored records, numerical results, independent audit, and inspected figures.
- Operational closeout, original collector-failure evidence, and byte-preserving local recovery evidence.
- The preceding CTI pilot and prior-work assessment under sibling `reports` directories.
- A ready-to-use blinded human-review form and handoff. Actual human reviews are still pending.

The pre-inference Git commit is `e00c27390cc6e64df3b8241fe1f9f9f450b28615` on local branch `CTI-External-Validation-20260918`. The completed outputs are committed afterward on the same branch. Remote publication is not part of this package closeout.

`SCIENTIFIC_FREEZE.json` binds 50 pre-inference files. `FREEZE.json` additionally binds the cloud runtime. `PACKAGE_MANIFEST.json` inventories the delivered package by byte length and SHA-256; it excludes itself and the external ZIP checksum receipt to avoid circular hashes. Post-run report additions, chart rendering, audit, and collection recovery do not change the frozen experiment.

## Reproduce scoring without AWS

From the extracted package root, use Python 3.11 with NumPy. The recorded analysis environment used NumPy 2.4.6. Scoring reads saved model answers; it does not call an API or start a cloud host.

```powershell
python reports/cti_external_validation_20260918/analyze_external.py --outputs reports/cti_external_validation_20260918/execution_outputs
python reports/cti_external_validation_20260918/audit_external_results.py --outputs reports/cti_external_validation_20260918/execution_outputs --report new_independent_audit.json
```

Run in a copy of the package to preserve the delivered result timestamp and hashes. The independent auditor refuses to overwrite an existing audit receipt. Its counters and gate checks are independent; it does not rerun bootstrap draws. `summarize_external.py` regenerates the numerical report, but the delivered report also contains labeled post-run closeout notes added afterward. Figure generation uses Matplotlib 3.11.1.

Full retrieval reconstruction and model inference additionally require the historical inputs named in the audits, the pinned ATT&CK corpus, and model weights. Those external dependencies are identified by path/revision/hash; this is not an offline copy of all model weights or the entire historical repository. The raw result archive contains the Linux filenames `RUNTIME.json` and `runtime.json`; use the included Windows recovery helper when extracting it on a case-insensitive filesystem. The already recovered `execution_outputs` directory is ready for analysis.

## Research and review boundaries

Accuracy is agreement with released SecEval answers. The benchmark is public, includes shared source families, and does not establish independence from model pretraining or source documents. The method's algorithmic novelty and superiority to complete published checker systems remain unproven.

The full package contains answer keys and model outcomes. Give independent reviewers only the offline form and review instructions specified in [REVIEW_HANDOFF.md](REVIEW_HANDOFF.md), before revealing outcomes.

## Attribution

SecEval: Guancheng Li, Yifeng Li, Guannan Wang, Haoyu Yang and Yang Yu, *SecEval: A Comprehensive Benchmark for Evaluating Cybersecurity Knowledge of Foundation Models* (2023), [author repository](https://github.com/XuanwuAI/SecEval), [pinned dataset revision](https://huggingface.co/datasets/XuanwuAI/SecEval/tree/205dab7b0888a06f4b53ca7d9c7093e1326683e1). Dataset material is CC BY-NC-SA 4.0; code licensing is separate. See the earlier pilot's [attribution](../cti_checker_pilot_20260918/ATTRIBUTION.md) and [MITRE ATT&CK license](../cti_checker_pilot_20260918/MITRE_ATTACK_LICENSE.txt) for inherited materials.
