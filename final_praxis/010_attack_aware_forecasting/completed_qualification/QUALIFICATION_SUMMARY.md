# Candidate 010: completed qualification

**Decision: advance to a new, prospective development design. The proposed novel defense remains untested.** All three actual model modes completed, and the artifact auditor passed 51/51 checks. Source and CPU gates also passed before model execution. A [separately authored independent review](independent_review/INDEPENDENT_010_RESULTS_REVIEW.json) passed 20,026/20,026 checks; its exact source, validation receipts, prior partial reviews, and replay wrapper are included.

## Question and qualification scope

Can a causal monitoring procedure retain persistent sensor-attack evidence while recovering after legitimate changes? Published context protection and adaptive calibration already exist. A bounded update mass alone does not bound the change in a nonlinear forecast; any mathematical influence guarantee requires explicit sensitivity or perturbation assumptions. This qualification establishes reproducible baselines, executable public-data calibration, and the operational feasibility of native TimesFM 3. It does not establish the novelty or efficacy of the proposed constrained context-update modification.

The frozen QH1 observer/source comparison and QH2 synthetic persistence controls passed: 222 CPU checks, 20 original observer simulations, and all 10 predetermined persistence seeds. QH3 completed the full 20-seed original TimesFM 2.5 comparison and exact selected Chronos/W1ACAS public example. QH4 completed native TimesFM 3 finite/repeat/latency/memory gates. See [protocol](../QUALIFICATION_PROTOCOL.md), [runtime freeze](../RUNTIME_FREEZE.json), and [final audit](FINAL_ARTIFACT_AUDIT.json).

## Original TimesFM 2.5 results

| Policy | Attack alarms | Clean alarms | Episode hits |
|---|---:|---:|---:|
| historical_oracle_blend | 200/600 | 3/600 | 20/20 |
| rolling | 138/600 | 3/600 | 20/20 |
| alarm_only_blend | 200/600 | 3/600 | 20/20 |
| literal_freeze | 246/600 | 64/600 | 20/20 |

Each endpoint denominator is 600 positions from 20 matched simulations. All 4,800 endpoint records and 8,000 admission records are retained. Literal freezing increases clean false alarms as well as attack alarms. Equal endpoint totals for historical and alarm-only blending do not imply general equivalence: the historical path disables protection before known attack onset, whereas alarm-only blending actually modifies eight of 400 pre-onset positions in each matched stream. The complete action accounting is in [QUALIFICATION_SUMMARY.json](QUALIFICATION_SUMMARY.json).

This reruns reviewed released calculations with pinned contemporary assets, not a reconstruction of the authors' unspecified original software/checkpoint environment. Historical use of oracle onset is disclosed and separated from deployable controls. This is a development comparison of existing policies, not a test of our proposed new method.

## Native TimesFM 3 probe

Median batch latency was 0.128472 seconds; peak allocated GPU memory was 2.464 GiB; repeated forecasts differed by 0.0. On the prespecified +2 synthetic shift, three of 256 shifted positions alarmed, with none after the first 32 shifted positions and two alarms after return. This is consistent with adaptation to a predictable change on one fixed development probe. It cannot distinguish malicious intent from an identical benign observation stream. See [raw forecasts and receipt](new3/QUALIFICATION_RECEIPT.json) and [figure](figures/new3_persistence.png).

## Public-data calibration

The exact TSB-AD NAB example has 4031 rows, of which 3024 are scored after the fixed first-1007-row boundary. At fixed alpha 0.01, 21/343 anomalous positions and 39/2681 normal positions alarmed. All values, labels, target-window alignments and reported counts were checked against the pinned file. The underlying forecaster and adaptive optimizer were not reexecuted by the artifact auditor.

The released wrapper's n_epochs=1/epochs=2 mismatch was preserved and disclosed in the pre-inference A1 amendment. The source demo's label-informed best-PA-F1 threshold is omitted in favor of the frozen threshold; consequently these are not reproduced paper aggregate metrics. The entire selected series is development/reproduction data, not a heldout cyber test. Retained y_true arrays and per-position labels are derived NAB/TSB-AD data with [source attribution and licenses](licenses/NOTICE.md).

## Reproducibility and limits

The three modes used 2462.69 seconds of measured worker runtime in total; this excludes shared host setup and does not constitute an invoice. Per-mode timing, installed packages, source/model identities, complete raw rows and the artifact auditor are included. The root campaign records operational isolation, instance shutdown and cost separately.

The original auditor promoted float32 predictions to float64 before blending. Source review corrected this before original 2.5 artifact inspection, preserving the strict tolerance; the targeted and negative controls pass 11/11. See [auditor correction A2](../postrun/AUDITOR_CORRECTION_A2.json). The frozen worker and protocol were unchanged.

HAI metadata access expanded beyond the train1-only plan after model execution started. [Scope deviation Q1-D1](HAI_METADATA_SCOPE_DEVIATION.json) records the exact timestamp/header-only access, source hash, all eight file identities, and stopped further access. No additional sensor or label values were parsed. The filename train/test partitions are not chronological; any future date-based split must cite this post-start ledger and be frozen before sensor/label analysis. HAI raw data remain outside Git, and no heldout HAI model efficacy was inspected.

Reproduce the raw-row audit after retrieving the pinned external NAB example:

```text
python postrun/audit_qualification.py --cache EXTERNAL_CACHE --original25 completed_qualification/original25 --new3 completed_qualification/new3 --calibration completed_qualification/calibration --output completed_qualification/FINAL_ARTIFACT_AUDIT.json
python postrun/replay_independent_review.py --cache EXTERNAL_CACHE --output NEW_INDEPENDENT_REPLAY.json
python postrun/summarize_qualification.py
```

The first command validates hashes, complete row universes, arithmetic and chronology alignment without new inference; the independent replay command rebuilds the expected receipt layout and runs the separately authored reviewer without loading a model; the last command regenerates the descriptive summary and release manifest. Model reruns use the frozen [GPU runbook](../GPU_RUNBOOK.md) with fresh output directories and external asset caches.

## Next investment decision

Invest in a small frozen development experiment on the proposed causal modification, using explicit false-alarm and benign-recovery constraints and comparable simple baselines. These qualification results justify technical development, not selection as the primary Praxis. The persistence phenomenon, buffer protection, and adaptive calibration all have direct prior art; a successful new causal mechanism and a defensible evaluation remain necessary.
