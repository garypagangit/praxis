# Independent holdout qualification

Qualified September 21, 2026, before any model predictions on the new target.

**APT Sandworm is available for a fresh, descriptive binary transfer test. A new independent six-stage holdout is still unavailable.** We acquired the author flow CSV and documentation, checked their published checksums, and prepared the same 73 predictor fields used by the frozen SCVIC experiment. This preparation produces no predictive result.

The narrow question is: **After learning from SCVIC, do the existing models recognize attack flows in a different critical-infrastructure environment, and how many normal flows do they incorrectly flag?** It does not validate the earlier rare-stage improvement, missing-log resilience, early warning, or actor attribution.

## Qualified target: APT Sandworm

The [author dataset](https://zenodo.org/records/16911636) was released August 20, 2025. Its associated peer-reviewed paper appears in the May 2026 issue of *Future Generation Computer Systems*: Iturbe, E., Dalamagkas, C., Radoglou-Grammatikis, P., Rios, E., & Toledo, N. (2026). *A pattern-aware LSTM-based approach for APT detection leveraging a realistic dataset for critical infrastructure security*, 178, 108308. [DOI](https://doi.org/10.1016/j.future.2025.108308); [author institution record](https://dsp.tecnalia.com/items/fef77b59-2af3-4d55-8a64-31da54992344).

This is an independently generated critical-infrastructure capture from different authors and a different environment than SCVIC. Its testbed emulates a Wide Area Measurement System with industrial equipment and virtual machines. It represents one Sandworm-inspired campaign on February 18, 2025, not many independent incidents. The method in the base paper is sequence-aware; our frozen transfer uses individual flow statistics and does not reproduce its sequence experiment.

### Acquired bytes and actual labels

| Artifact | Size | SHA256 |
|---|---:|---|
| Author `SandwormAPT_flow_labelled.csv` | 1,342,640 bytes | `c2669e324fe94076a148d2942e86be97acfd7f39322e89bf267c554c530330b4` |
| Author `APT_Dataset_Readme.pdf` | 525,281 bytes | `a9e0dc3f1b45b249dc4f4c69ef0facc58f961e68d81c0499f0b3a829a29cf7f1` |

Both downloaded files match the MD5 checksums published by the author release. The 1.8 GB PCAP was not needed for this bounded flow-level test and was not downloaded. The original CSV, prepared arrays and raw row mappings remain private. [Public qualification receipt](SANDWORM_QUALIFICATION.json).

| Author label, exact spelling | Raw flows | Unique predictor rows |
|---|---:|---:|
| Normal | 2,096 | 2,054 |
| PHP_insecure_intrusion | 16 | 16 |
| smb_intrusion | 8 | 8 |
| rdp_intrusion | 7 | 7 |
| ssh_intrusion | 5 | 5 |
| remote_system_discovery | 1 | 1 |
| **Total** | **2,133** | **2,091** |

There are **37 attack flows** and 42 exact feature duplicates, all Normal. No identical predictor group has conflicting procedure labels. All 73 target predictors are finite numeric values. The timestamp range is February 18, 2025, 11:02:12.032482–11:23:27.458544; timestamps are retained only in private provenance, never used as predictors.

The [author README, pages 2 and 5](https://zenodo.org/records/16911636/files/APT_Dataset_Readme.pdf), explains that labels were assigned by correlating Caldera logs with network activity. Only procedures visible in the flow capture receive attack labels; endpoint-only attack actions are outside this labeling scope. These are procedure labels, not SCVIC's six classes. The CSV contains no exfiltration label, even though the emulation timeline includes an exfiltration action. Author labels are accepted for this evaluation, without a new human adjudication claim.

### Feature and independence checks

The [adapter](prepare_sandworm.py) selects the frozen SCVIC columns in their existing order. Identifiers, IP addresses, ports, timestamps, labels and all Idle statistics stay excluded. Ten target-only fields are also excluded. No target statistics are used to scale, impute or select predictors. At model execution, the imputer must be fitted only on the original source fitting support.

The [73-field compatibility table](FEATURE_COMPATIBILITY.md) and [machine-readable metadata](FEATURE_COMPATIBILITY.json) list every meaning and unit convention. The names and documented field meanings align. **Exact CICFlowMeter revisions, timeout settings and implementation equivalence are not qualified.** Several time and bulk units are conventions inferred from field definitions, not explicit version-specific metadata. No unit conversion is guessed. The experiment therefore includes possible extractor shift as well as environment shift.

SHA256 covers the complete ordered numeric predictor row after the same float64 canonicalization used in SCVIC. **Zero target rows overlap exactly with any of the 153,919 frozen SCVIC rows.** This excludes exact predictor reuse; it does not eliminate correlated or near-duplicate flows within a capture, prove independent incidents, or establish absence from foundation-model pretraining.

The primary query contains all 2,091 unique rows, sorted by predictor hash. `raw_to_unique` maps the 2,133 author rows to this fixed query. A secondary analysis reweights these predictions by raw multiplicity. Foundation predictions may depend on query batching, so this sensitivity is not described as a separate prediction run in raw CSV order.

### Rights metadata discrepancy

The [Zenodo API](https://zenodo.org/api/records/16911636) and landing page license field identify **CC BY 4.0**. The same [landing page copyright field](https://zenodo.org/records/16911636) says **CC BY-NC-ND 4.0**. The author README does not resolve this conflict. The paper's license is not a substitute for the dataset's rights metadata.

The first private acquisition receipt copied only the API field. That receipt is preserved; a separate hash-bound `RIGHTS_AMENDMENT.json` records both fields and corrects the incomplete summary. This evaluation uses private noncommercial processing and publishes only code, provenance, hashes and aggregate measurements. Original and adapted data are not redistributed. We do not claim that the conflicting fields have been resolved or that new permission was obtained.

## Frozen evaluation plan

[Protocol](protocol_sandworm_transfer.json); [runner](run_sandworm_transfer.py).

1. Reuse the ten original SCVIC fitting supports: 32 examples from each of six classes, including NormalTraffic, for 192 fitting labels per seed.
2. Reuse the original source-only inner-CV winner between XGBoost and LightGBM and its selected parameters for each seed. Do not retune or select a comparator on target results.
3. Compare that tree model with the unchanged primary TabICL v2 checkpoint/backend, four estimators, CPU, one model worker and fixed 1,024-row query chunks. Freeze code/protocol/checkpoint/data receipts before target fits or predictions.
4. A flow is predicted as an attack when the original six-class argmax is not NormalTraffic. Ranking metrics use `1 - P(NormalTraffic)`. No Sandworm fitting, calibration, threshold tuning, class remapping or model selection is allowed.
5. Report binary macro-F1, attack F1, precision, recall, ROC-AUC, average precision, normal false-positive rate and TP/FP/TN/FN. Report each original attack procedure's detected/missed counts. Show all seeds, their means and ranges, and both unique and raw-multiplicity views.

There is no newly chosen success threshold. Ten seeds are ten source-fitting subsamples tested on the same target capture, not ten independent target incidents. With only 37 attack flows, especially one discovery flow, per-procedure estimates must be read as exact observed counts without broad stage-performance claims.

A secondary operating-point diagnostic is predeclared for when matching full source-calibration predictions are available: use only the 29,929 source-normal calibration scores to fix a conservative empirical 1% tail threshold, then measure its target attack recall and false alarms. It uses additional source calibration labels; it does not change the primary argmax result or guarantee a 1% target false-positive rate under shift.

### Prepared artifact contract and verification

Canonical private prepared directory: `tabular_followup_v1/sandworm_prepared_v3`.

- `DATA.npz`: `3b3779f4d0b9c77841dddaf51598447b75f09569da19d6bc5ddd5f23d5a1e00a`.
- `MANIFEST.json`: `debacd905ea707cd198854c4192e27492ddf0e89279f240f23ff98736ad144f2`.
- NPZ keys: `X`, `y_binary`, `procedure_labels`, `group_sha256`, `feature_names`, `raw_to_unique`. All arrays load with `allow_pickle=False`; strings use fixed Unicode dtypes.
- Four adapter tests pass: canonical fingerprints, conflicting-procedure rejection, raw mapping reconstruction, and safe archive round-trip. Actual prepared row fingerprints were independently recomputed and passed.

Two development attempts remain preserved privately: the first failed manifest serialization; the second contained object-dtype strings incompatible with the loader. Neither generated model fits or target predictions. The corrected third artifact is the only protocol-bound target. These were preparation defects, not failed scientific experiments.

## Other sources checked

| Candidate | What is verified | Why it is not the fresh six-stage holdout |
|---|---|---|
| SCVIC author test CSV | [DataPort](https://ieee-dataport.org/documents/scvic-apt-2021) lists a test file; [DataCite](https://api.datacite.org/dois/10.21227/g2z5-ep97) lists CC BY 4.0. Local training file and prior source search are available. | Author test is absent locally; anonymous artifact access requires login/subscription. Original linked GitHub returns 404. No lawful accessible copy was qualified. Third-party training-derived splits are not substituted. |
| Unraveled | Peer-reviewed [Computer Networks paper](https://doi.org/10.1016/j.comnet.2023.109688); [author repository](https://gitlab.com/asu22/unraveled), commit `d2ea90055d82fa448ab20588a13e3ec8bfd74816`; explicit GPL-3.0 data README link. All 173 local CSVs match their pinned Git blobs after repository line-ending normalization. | Independently generated captures, but all 173 source files were already represented in the earlier GML cache. It can support a disclosed external-dataset replication, not an untouched confirmation holdout. NFStream features also differ from the frozen 73 CICFlowMeter features. |
| Windows-APT-2025 | Peer-reviewed [2026 Data in Brief article](https://doi.org/10.1016/j.dib.2026.112569), [author dataset page](https://cybersciencelab.com/datasets/windows-apt-2025/), and [Mendeley release](https://data.mendeley.com/datasets/b8fmtzvpy8/4). | The checked artifact API returned HTTP 403; raw files were not acquired/qualified. Host Wazuh/Sysmon logs are not a compatible flow-feature holdout. Scenario separation, benign labels and possible rule-label leakage need their own qualification. |
| FullAPT-2025 | [Public repository](https://github.com/blinkomaniak/FullAPT-2025-Cybersecurity-Dataset), pinned `17de8408970a5b02a3c35f37db1e03bdf461dcdd`; MIT code license. | Actual 219-entry public tree has zero CSV files despite README dataset claims. No verified peer-reviewed dataset paper or downloadable flow release was found. |
| DSRL-APT-2023 | [Author release](https://github.com/shadab75/DSRL-APT-2023) and previous E0 audit. | Synthetic CTGAN derivative of DAPT2020; not independent real-data confirmation. |
| S-DAPT-2026 | [Withdrawn arXiv record](https://arxiv.org/abs/2601.06690) and [later SSRN posting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942). | Corrected analysis, actual licensed artifacts and revised claim support remain unqualified. A later manuscript posting alone is insufficient. |

### Unraveled audit: a future replication route

The bounded read-only audit counted **6,877,157 rows, 173 files, 31 capture directories and 3,723,532,930 bytes**. The source is independently generated relative to DAPT2020/SCVIC, with emulated benign activity and attack profiles; it is not the CTGAN derivative. [Aggregate audit](UNRAVELED_QUALIFICATION.json); [audit script](audit_unraveled.py).

Raw stage counts include 6,766,747 Benign, 11,676 Normal, 34,794 Reconnaissance, 27,445 Lateral Movement, 27,118 Establish Foothold, 7,522 Data Exfiltration and 362 Cover up. Another **1,493 rows contain numeric stage strings** (`6`, `26`, `33`, `7`) that must be investigated and cannot silently be treated as valid stage labels. The earlier cache retained only a sampled fraction of benign traffic, so it does not preserve raw prevalence.

The author README explains that internet-bound traffic may be recorded on multiple network interfaces. Capture directory dates also overlap. A later replication needs a separately frozen adapter that groups overlapping capture periods and interfaces, checks cross-group duplicate flows, resolves anomalous stage fields from source documentation, and restores natural prevalence. It cannot simply split source filenames or randomly reuse the earlier cache. Because all files were already exposed in prior GML work, this route must remain a disclosed replication rather than an unseen holdout.

## Reproduce qualification without fitting models

Use `acquire_sandworm.py --output <fresh-private-directory>` to download only the author flow CSV and README and verify their published checksums. The acquisition helper now records the rights caveat; the original acquisition receipt remains unchanged.

Run `prepare_sandworm.py --source-csv <author-csv> --scvic-prepared <frozen-source-directory> --output <fresh-private-directory>`. It rejects changed source hashes, missing columns, conflicting labels and exact source-target feature overlap. It never overwrites a populated prepared directory.

Run `qualify_sandworm.py --private-root <tabular_followup_v1> --output <metadata-output-directory>` to regenerate metadata-only reports against the canonical prepared artifact and preserve the rights amendment. No classifier is fitted by these qualification tools.
