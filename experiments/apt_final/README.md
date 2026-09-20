# APT final

This is the new APT experiment program on Git branch **`APT-final`**. It preserves the two supplied proposals and keeps their claims separate from measured results.

The [normal-reference stability comparison](normal_stability/README.md) is **completed and independently audited: NO-GO for the fixed repair family**. None of the nine variants met all declared detection and false-alert requirements on either CADETS or THEIA. Read the [final report](normal_stability/results/gpu_stability_20260920/REPORT.md), [complete results](normal_stability/results/gpu_stability_20260920/FULL_RESULTS.md), [AWS closeout](normal_stability/results/gpu_stability_20260920/AWS_CLOSEOUT.md), and [closure/next actions](NEXT_ACTIONS.md).

Pooled calibration lowered masked normal false alerts from about 50% to below 1%, but MLP malicious-entity recall fell to 0.079% on CADETS and 0.030% on THEIA. A THEIA graph-model average improved, yet repeated-case and cross-dataset reliability still failed. The family is closed; no extra checker or threshold variant is pending. All four attempts are verified stopped, with approximately $1.631 in compute for this comparison, excluding storage and transfer.

The [earlier scoring follow-up](embedding_baseline/results/gpu_scoring_20260920/REPORT.md), [initial negative pilot](native_graph/results/gpu_pilot_20260920/REPORT.md), original Unraveled hold, and previous registrations remain preserved. No novelty, independent campaign confirmation, or APT actor identification is established.

## What is built

| Component | Purpose | Scientific status |
|---|---|---|
| Normal-reference stability | Separate normal fitting/calibration/validation; crossed model/bank seeds; missing-relationship repairs | Completed, audited, and closed: zero of nine candidates passed on either dataset. |
| Frozen embedding scoring | Exact normal-reference nearest-neighbor scores using unchanged trained encoders | Completed and audited; strong THEIA signal, failed cross-dataset readiness and robustness. |
| Native graph GPU pilot | Benign-trained detectors and fixed selectors on CADETS/THEIA with missing relationships | Completed on AWS; independently audited development result. Poor recall and no useful checker gain. |
| Three-candidate registry | Local LLM deployment; prediction stability; structural/semantic/hybrid stage representations | Proposed tracks with literature and data prerequisites. Not three implemented or successful detectors. |
| E0 data audit | Inspect available Unraveled sources, stage support, timestamps, potential linkage, and campaign independence | Actual local-data audit completed; **HOLD_DATA_CONTRACT**. |
| E1 edge-information experiment | MLP versus GIN with real, rewired, or self-only edges | Development engine; synthetic qualification, no new real-data efficacy result. |
| E2 degradation experiment | Paired fixed-model replay with missing/delayed graph edges and relation outages | Edge-only perturbations; full source/feature loss is not implemented. |
| E3 routing experiment | Static and learned quality policies against fixed/simple controls | Saved-prediction selection; cost proxies do not demonstrate deployed compute savings. |
| E4 frozen transfer replay | Apply frozen models and policy to separate confirmation files | Software path only; real confirmation is not released or registered. |

The E0-E4 sequence is the **telemetry-quality routing program** in the second attachment. It does not silently stand in for experiments on all three topics in the first attachment.

## Initial native-pilot finding

The native graph pilot did not establish a useful detector or checker. Clean-graph GIN recall averaged approximately **0.10% on CADETS** and **0.043% on THEIA** at thresholds fixed using benign calibration. The fixed quality selector made essentially the same alert decisions. These are negative results for this representation, scoring method, and checker; they do not establish that all routing methods fail. The latest verification passed **50 software tests**. See the [full result report](native_graph/results/gpu_pilot_20260920/REPORT.md).

### Original Unraveled track: still on hold

E0 recounted **435,488 cached Unraveled rows** and inspected bounded source samples from **173 flow files and 59 host files**. Existing source metadata does not establish independent APT campaigns or a validated flow/host join. Mixed timestamp formats and unresolved identity mappings must be resolved before relying on those relationships. All cached `Signature` values were empty.

Validated join rate and clock-skew estimates remain **unknown**. Zero candidate coincidences in prefix samples does not prove the dataset cannot be joined. Read the exact [E0 result](results/e0_20260919/E0_RESULT.json) and [data-quality memo](results/e0_20260919/E0_REPORT.md).

The current E0 tool is an inventory/recount audit, not a qualified normalized-data release validator. `readiness.py` blocks real-data E1-E4 calls until the mapping/review artifacts support a tested release adapter. Editing HOLD to PASS cannot unlock a model run. This makes the missing work explicit rather than hiding an unverified assumption in training code.

## Research record

- [Original candidate ideas](inputs/candidate_ideas.txt) and [original E0-E4 sequence](inputs/experiment_sequence.txt), preserved byte-for-byte with [source hashes](inputs/SOURCE_MANIFEST.json).
- [Three candidate tracks](candidates.json), including their actual novelty risks.
- [Literature and design audit](docs/LITERATURE_AND_DESIGN_AUDIT.md).
- [Corrected development protocol](docs/PROTOCOL.md).
- [Normalized input and evidence contract](data/DATA_CONTRACT.md).
- [Development configuration](configs/development.json) and [synthetic qualification configuration](configs/smoke.json).
- [Committed development registration](REGISTRATION.json), binding the exact source, configuration, and protocol used for the initial freeze.
- [Initial Unraveled software qualification](results/qualification_20260919/README.md): **32 tests passed**, plus the complete synthetic E1-E4 command-line run; [historical receipt](results/qualification_20260919/QUALIFICATION.json).
- [Completed native graph GPU experiment](native_graph/results/gpu_pilot_20260920/REPORT.md), including independent saved-evidence verification and a separately labeled post-hoc diagnostic.

The literature audit corrects several supplied premises. OCR-APT already reports local-model comparisons; PIDSMaker already studies instability; dataset availability and label validity still require verification. These are reasons to narrow the contribution, not to rename existing methods as new.

## Run the software

The commands below reproduce the original Unraveled audit and synthetic engine. For the completed GPU experiment, use the separate [native graph instructions](native_graph/README.md). Use Python 3.11+; E0 and status use the standard library. E1-E4 qualification also requires the packages in `requirements.txt`. Use a dedicated virtual environment. All output paths below must be new; scientific receipts are never overwritten.

```powershell
python experiments/apt_final/run.py status

# Read-only local-data audit. No model training or cloud calls.
python experiments/apt_final/data_audit.py --workspace "C:/Users/garyp/OneDrive/Documents/codex" --output "C:/w/apt_e0_recheck"

# Entire software pipeline on explicitly synthetic data.
python experiments/apt_final/run.py smoke --output "C:/w/apt_final_smoke_recheck"

# Meaningful guard and engine tests.
python -m unittest discover -s tests -p "test_apt_final*.py" -v
```

An audit can finish successfully while its scientific status remains HOLD. Always inspect `E0_RESULT.json.status`; shell exit code zero means the audit executed, not that the data passed.

### Original Unraveled registration and later real-data execution

The registration command accepts only exact committed code/config/contract bytes. A new registered configuration is needed after any operative change.

```powershell
python experiments/apt_final/run.py register --output "C:/w/apt_development_registration.json"
```

It records a **development configuration freeze**, not a completed confirmatory preregistration. The initial E4 margin, verified exposure, independent units, and data-release adapter are not ready. Only after those gates are resolved should a separate real-data run use `run --stage E1` with registered configuration, normalized rows/edges, and a verified E0 receipt. Run `--help` for complete stage arguments. E2 and E3 bind upstream artifacts; E4 requires an additional policy-bound readiness receipt and compatible separate confirmation files.

## Closure and broader work

The fixed normal-reference stability study, its independent audits, exact replay check, public evidence package, and verified cloud shutdown are complete. No immediate dataset purchase, manual labeling, or AWS task is required from Gary to close it. See the [final decision](normal_stability/results/gpu_stability_20260920/FINAL_DECISION.json).

A broader graph-learning praxis remains a separate research decision. The completed method should not be advanced as a demonstrated successful or novel checker. Any different method or independent confirmation would need its own stated contribution, data evidence, and new frozen comparison; it is not an unfinished step of this study.

The original Unraveled campaign/identity/time/link review remains optional unless that track is reopened. Concrete external-review steps and an evidence-recording form are in [human requirements](normal_stability/analysis/HUMAN_REQUIREMENTS.md). No dataset-author message or independent human review was performed. No paid model API or comparative GPU speedup is claimed.
