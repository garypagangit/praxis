# DEDALE acquisition and external stress qualification

Completed 21 September 2026. **Data acquired and prepared; no models fitted, calibrated or evaluated by this work.**

## Decision

**Go for a small, source-locked external stress test. No-go for independent proof of lateral-movement protection.** The acquired data contain only **four lateral-movement flows from one documented PrintNightmare execution**. Multiple flows, two substeps and additional fitting seeds do not create independent attacks. A supervised within-DEDALE lateral train/test comparison is unsupported by this capture.

The ready stress input contains those four unique lateral feature groups and 100,000 deterministically sampled unique benign feature groups from the same attack day. It supports reporting exactly how many of four were detected and how often sampled normal groups were flagged. It cannot establish a tight lateral noninferiority margin, broad attack reliability or deployment readiness.

## Author source, rights and bounded acquisition

The official [DEDALE record](https://doi.org/10.57745/Y5JLDG) is released version **2.0**, dated **20 March 2026**, with **CC BY 4.0** in its terms. The [paper](https://doi.org/10.1007/978-3-032-16092-8_1) was published online 1 May 2026. The capture itself spans December 2024–January 2025. The paper describes two benign weeks, an eight-day APT campaign, then six benign days.

The author's `cicflowmeter_green_internal.zip`, file ID `717871`, is 3,006,480,661 bytes. Its advertised whole-archive MD5 is `e2152af582e903b4d3fbe0f36672feaf`. Rather than acquiring the whole archive, [acquire.py](acquire.py) validates HTTP 206 byte ranges and extracts specifically named ZIP members. Every acquired member passed ZIP CRC32 verification and received a SHA-256. **The entire archive's MD5 has not been verified.** No PCAPs were downloaded.

[The acquisition plan](ACQUISITION_PLAN.json) selected all fourteen final evaluation days, D15–D28, plus one Monday from each earlier benign week, D1 and D8. Selection used the author chronology and archive sizes, before model outcomes. Sixteen tables occupy **6,644,107,407 uncompressed bytes**. The conservative cumulative download ledger is **1,831,346,622 bytes**, including a 1 MB allowance that covers metadata and initial probes, below the 2,000,000,000-byte limit. See [SOURCE_RECEIPT.json](SOURCE_RECEIPT.json) for source snapshots, hashes and licenses.

## Labels and complete subset counts

The [author labeling repository](https://gitlab.inria.fr/mlanvin/dedale_labeling), pinned at commit `f148722eb5908fc17841dc3c8be1591c5c3e59a6`, explicitly includes a CICFlowMeter labeling script. Actual downloaded tables already contain `label`, `step`, `attack_step`, `tactic`, `technique` and `comments`. Therefore these artifacts require **no inferred Zeek-to-CICFlowMeter label join**. The author code is GPL-3.0; the data record specifies CC BY 4.0.

| Author category | Raw flows in the acquired 16 days |
|---|---:|
| Benign, label 0 | 10,362,041 |
| Attack, label 1 | 71 |
| Attack-related but not inherently malicious, label 2 | 21 |
| **Total** | **10,362,133** |

The 71 attack flows comprise initial access 1; command and control 58; discovery 1; lateral movement 4; collection 5; exfiltration 2. Label 2 remains a separate category; it is not silently called normal or malicious. D1/D8 contain 1,650,599 benign flows and no attacks. The full final two weeks contain 8,711,442 benign, 71 attack and 21 attack-related flows.

All four lateral flows occur on **D17, 8 January 2025**. The author's script identifies one PrintNightmare execution and two TA0008/T1210 substeps: one flow for the client exploitation and three for obtaining the malicious DLL. These are labels attached using execution times, host pairs and, for one substep, ports, with a three-minute time margin. They are not four independently performed attacks or four independent manual adjudications. Neither neighboring discovery nor command-and-control flows were relabeled as lateral movement to increase support.

[QUALIFICATION.json](QUALIFICATION.json) contains per-day counts, author-step counts, feature mapping and integrity receipts. Its SHA-256 is `949e133d1ffa4319cd0d66d7521c627de673b007c98cdb53cf63ea213c8b2e38`.

## SCVIC feature compatibility

All **73 source predictors** are present and numeric. There are 71 identical column names and two author-documented renames: `Protocol` → `proto`, and `Flow Duration` → `duration`. The labeling parser does not rescale duration; the pinned CICFlowMeter implementation measures it in microseconds. The extractor repository is [GintsEngelen/CICFlowMeter](https://github.com/GintsEngelen/CICFlowMeter), revision `4dd5319ad36457010d7a406505790b17a5828108`.

No nonfinite predictor cells were found across the acquired subset. Identifiers, addresses, ports, timestamps, author labels, comments and extra target-only features remain outside the 73 predictors. The original source's exclusion of Idle features is retained. No target-derived scaling or imputation is fitted.

**Limit:** SCVIC's exact extractor revision/settings are still unverified. Matching feature names, documented meanings and units permit a transparent source-transfer stress check; they do not establish identical feature-generation implementations or remove domain shift. DEDALE uses a corrected extractor. Results must retain this limitation.

The full subset had zero exact overlaps with source feature fingerprints. Preparation additionally recomputed every source fingerprint directly from original `X`, rather than trusting the saved hashes alone, and verified equality to the source receipt. Equality means SHA-256 of ordered little-endian float64 bytes after nonfinite-to-canonical-NaN and signed-zero-to-positive-zero normalization. It uses **no numerical tolerance** and does not prove absence of near duplicates or collection dependence.

## Frozen day17 stress preparation

[PREPARATION_PROTOCOL.json](PREPARATION_PROTOCOL.json) was written before extraction. SHA-256: `113cc66a5398f93adf8b48f958b06d247ee354dfc3eb72da46345162146aca7e`. The preparation code and input hashes are bound in that protocol. The fixed source fitting seed is **20260921**. Model selection, fitting and thresholds must remain source-only; the baseline is evaluated regardless of success, and a candidate is evaluated only if the source study selects a feasible candidate.

[prepare_stress.py](prepare_stress.py) performs the following declared operations:

1. Reproduce the original source's canonical feature hashes and exclude any matching target feature group.
2. Group day17 rows by the canonical 73-feature hash. Drop an entire group if its author label/stage/tactic/technique signatures conflict.
3. Keep one representative per remaining group, recording raw multiplicity. Retain only author benign and author label-1 TA0008 groups; exclude other attack stages by the fixed scope.
4. Keep every eligible lateral group. Select at most 100,000 normal groups by the lowest SHA-256 of the ASCII hexadecimal feature fingerprint, with a deterministic fingerprint tie-break. Sort the output by feature fingerprint.

| Day17 preparation count | Result |
|---|---:|
| Raw normal / lateral / other-stage rows | 851,204 / 4 / 43 |
| Unique normal / lateral / other-stage feature groups | 794,752 / 4 / 43 |
| Duplicate excess rows | 56,452 |
| Source-overlap rows excluded | 0 |
| Conflicting-label rows excluded | 0 |
| **Selected normal / lateral groups** | **100,000 / 4** |

The normal groups selected represent 109,468 raw rows; the four lateral groups each occur once. **The primary sample is a stratified sample of unique feature groups. Its precision and F1 are not deployment-prevalence estimates.** Raw-flow sensitivity would require explicitly specified weighting; multiplicity does not turn a deliberately enriched sample into the original traffic stream. Preserve false-positive counts/rates and detected/missed lateral counts as the clearest descriptive outcomes.

The private output directory is `dedale_stress_prepared_v1` under the private `lateral_protection_v1` data root. It contains:

- `DATA.npz`: `X` float64 `(100004,73)`; `y_binary` int8, **0 = author benign, 1 = author lateral attack**; `feature_names`, `group_sha256`, `source_row_indices`, and `multiplicity`. All arrays load with `allow_pickle=False`.
- `MANIFEST.json`: aggregate counts, source/protocol/code bindings and limitations. Its public aggregate-only copy is [STRESS_PREPARATION_RECEIPT.json](STRESS_PREPARATION_RECEIPT.json).
- `COMPLETE.json`: final hashes, written after data and manifest.

| Private artifact | SHA-256 |
|---|---|
| DATA.npz | `245e2da96cce476173cd2cc5b20278d36bf8cef4b302ae60fefbc29fcad099bd` |
| MANIFEST.json | `7e65d58ac79b421fe151a5a59c591050859f1ee001142b6f5d711a016deafcbb` |
| COMPLETE.json | `429d27132874ed81360735c2f61f93191909069039dd5ef9c4f749b700c83cd0` |

Three synthetic integrity tests passed: duplicate/conflict/source-overlap handling and non-object outputs; refusal of inconsistent source hashes; rejection of fractional author labels. No model performance was used to choose, prepare or test these rows.

## Concrete next action

Freeze an evaluator that loads the source-selected baseline and, if feasible, candidate; verifies these receipts and the exact feature order; applies the already fixed source thresholds once; and reports false alarms out of 100,000 normal groups plus detections out of four lateral groups. Report all outcomes, including zero detections. Label this **external stress evidence**, while reserving independent confirmation for new executions or another qualified dataset with adequate lateral-event support. Do not tune on this target or reinterpret a four-of-four result as broad reliability.
