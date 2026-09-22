# Available exfiltration data and attack-stage timeline qualification

Qualified September 22, 2026. **No models fitted, no new model outcomes inspected, and no previous data, split, protocol, or result altered.** Counts and source bindings are in [DATA_QUALIFICATION.json](DATA_QUALIFICATION.json).

## Decision in plain language

**We can test engineered exfiltration features and a stage-specific classifier ensemble now on SCVIC.** We can also illustrate the recorded DEDALE campaign and perform a tiny source-locked external exfiltration check. The available data do **not** establish an independent test that a system reliably follows an adversary through stages or provides early warning.

| Available source | Actual exfiltration support | Feasible now | Main boundary |
|---|---|---|---|
| SCVIC author training CSV and prepared 73-feature data | **527 unique exfil flows: 316 fit, 105 calibration, 106 development test** | Matched-budget feature/model comparison; held-partition flow-stage ensemble evaluation | Previously examined source data; no qualified independent execution IDs or author holdout |
| DEDALE acquired 16 days | **Two exfil flows, one execution, one day, one campaign** | Count-only source-locked stress; retrospective campaign timeline with explicit author labels | No independent target training/test split or reliable population recall estimate |
| AIT local annotated intranet slices | **Zero exfil labels** | Other recorded step tasks remain available | Exfiltration must not be inferred from webshell, escalation, or attacker HTTP labels |

## SCVIC: usable feature data, limited sequence evidence

The local raw CSV contains 259,120 rows. Its SHA-256 was rechecked against the preparation manifest: `a67b7a24196fc8c9e3b15ec7cf7b48b6a62f316fe24fc05fd9067dc745b3cf6e`. The prepared data contain **153,919 unique nonconflicting groups and 73 predictors**; SHA-256 `8e8a7474d4db03b78977a3c6a48be083d60d7648dd7548788037db721e80e565` was reverified. The [original qualification](../tabular_batch/E0_DATASET_GATE.md) and [preparation receipt](../tabular_batch/SCVIC_PREPARATION.json) retain the split and exclusions.

Private inputs:

- Raw author training file: `C:/Users/garyp/Downloads/SCVIC-APT-2021-Training.csv`.
- Prepared immutable input: `C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared/DATA.npz`.

The NPZ contains `X`, `y`, `split`, `group_sha256`, `classes`, and `feature_names`. Classes are DataExfiltration, InitialCompromise, LateralMovement, NormalTraffic, Pivoting, and Reconnaissance. It contains **no host or timestamp sidecar**. This review recomputed the original ordered little-endian float64 fingerprints, canonicalizing nonfinite values and signed zero. **Every one of the 153,919 prepared groups links to at least one raw CSV row.** A duplicated feature group can correspond to multiple raw events; retain that one-to-many relationship rather than inventing a unique event time.

All 527 exfil rows have unique predictor fingerprints. Their source timestamps cover **October 21, 2015, 10:21:00 to 23:01:02**, with 356 distinct timestamp strings, three source hosts, three destination hosts, and three directed host pairs. These are **not evidence of three independent campaigns**. No round/execution identifier has been qualified. The file also contains 220 normal rows dated January 17, 1970; normal timestamps mix minute-resolution slash strings and second-resolution ISO strings. The timestamp timezone and source extractor revision remain unverified.

Some stage records share exfil endpoints: all lateral rows share at least one exfil endpoint, whereas **none of the initial-compromise rows do**. There are shared directed pairs with lateral movement, pivoting, and reconnaissance, but shared addresses and ordering alone do not establish the full causal chain. A graph can display observed relationships; it cannot label them verified attacker movement without stronger linkage evidence.

The frozen split is feature-group-stratified, not chronological or campaign-held-out. Prior experiments have already examined its calibration/test outcomes. New frozen development experiments can compare engineering choices consistently, but another random partition would not create independent confirmation. The [SCVIC dataset paper](https://doi.org/10.1109/LNET.2022.3185553) supports the dataset's publication provenance; it does not validate a locally inferred sequence. The source record identifies CC BY 4.0; the local training bytes were not originally verifiable against an author checksum.

## DEDALE: a documented campaign with very little exfil support

The [author dataset](https://doi.org/10.57745/Y5JLDG), version 2.0, is CC BY 4.0. The [published paper](https://doi.org/10.1007/978-3-032-16092-8_1) and [earlier local acquisition qualification](../lateral_protection_experiment/dedale/QUALIFICATION.md) describe its provenance. The acquired days are D1, D8, and D15-D28: **10,362,133 flows**, comprising 10,362,041 author-benign, 71 attack, and 21 attack-related rows. Attack-related label 2 remains separate from benign and malicious truth.

The 71 attacks comprise initial access 1, command and control 58, discovery 1, lateral movement 4, collection 5, and exfiltration 2. **Both exfil flows occur on D20, January 11, 2025, and belong to author step 16, TA0010/T1041, one documented exfiltration execution.** The raw D20 CSV was directly reread and its acquired hash verified: `b6da7a800f43595c997e57265e2cd58df3bc56fa0869f83cac0b4003b9cf5b1b`. It contains 22,766 benign flows, two exfil flows, and one C2 flow. The two exfil predictor fingerprints are distinct; this does not make them independent attacks.

The private member is `lateral_protection_v1/dedale_qualification/members/717871_green_internal_D20_2025-01-11_output_green_internal.pcap_Flow_labeled.csv` under the private benchmark data root. The rows retain `date`, `uid`, source/destination addresses and ports, `ts`, and `duration`, plus author `label`, `step`, `attack_step`, `tactic`, `technique`, and `comments`. All 73 source predictors map, with the already documented Protocol/proto and Flow Duration/duration renames. Prior full-subset qualification found no exact SCVIC feature overlap; the exact source extractor remains unknown.

The pinned [author labeling code](https://gitlab.inria.fr/mlanvin/dedale_labeling) uses UTC scheduled action times, host pairs, designated ports, a plus/minus-three-minute window, and both flow directions. This review inspected the CICFlowMeter labeling script at commit `f148722eb5908fc17841dc3c8be1591c5c3e59a6`. One scheduled T1041 action labels the two flows. These are source-rule labels, not two independently adjudicated outcomes.

The exfil flows start approximately **11:00:14.936433 and 11:00:15.247102 UTC**; durations range from **0.118473 to 14.287847 seconds**. Full-flow byte/rate features therefore include information arriving after the start timestamp. The actual exporter availability time has not been qualified. For an illustrative replay, use completed-flow timing and disclose its limits; do not claim real-time warning from a score plotted at flow start.

A retrospective chronology can show author initial access on D15, discovery/lateral activity on D17, collection on D19, and exfiltration on D20, with C2 interleaved. Keep **author truth** and **model predictions** visually separate. DEDALE's C2 and collection labels have no direct counterpart in the six SCVIC classes; do not relabel them as Pivoting or DataExfiltration to force a sequence or improve a score.

## AIT check and immediate experiment boundaries

The local `partial_lds` directory has 32 annotation files from eight runs and 1,717,645 annotated line records. All were parsed successfully. Its twelve label names cover foothold, scanning, attacker HTTP, webshell, and escalation; **none denotes exfiltration**. The overlapping `lds_core` subset has 16 files and 433,186 annotated records, also without exfil labels. Coverage expansion/probe directories have no acquired annotation files. Do not sum overlapping subsets as independent evidence. The [pilot report](../results/pilot_v1/REPORT.md) already records this scope.

For the immediate SCVIC experiments, derived features can use the existing byte/packet totals, directional shares, packet-size variation, duration, and rates. Freeze zero-denominator, nonfinite, and transform rules; fit imputation/scaling on fitting data only. **Forward direction does not automatically mean outbound transfer.** Keep addresses, timestamps, file/day IDs, and all labels outside predictors. Use existing feature-group boundaries, equal fitting budgets, and fitting-only model choice; report exfil precision/recall/F1/AP and false positives from benign and other attack stages. A stage ensemble is a flow-classification experiment unless separate sequence supervision is qualified.

DEDALE can then support a **source-locked two-flow exfil stress**, after all source features/models/thresholds are fixed. Preserve other attack stages as a separate challenge instead of silently calling them benign. No target tuning, independent-execution claims, or positive selection based on those two outcomes is justified. A stronger progression study needs independently generated campaigns, trustworthy host/time linkage, and feature availability at each decision time before collection is treated as confirmation.
