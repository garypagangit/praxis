# APT final

This is the new APT experiment program on Git branch **`APT-final`**. It preserves the two supplied proposals and keeps their claims separate from measured results.

## What is built

| Component | Purpose | Scientific status |
|---|---|---|
| Three-candidate registry | Local LLM deployment; prediction stability; structural/semantic/hybrid stage representations | Proposed tracks with literature and data prerequisites. Not three implemented or successful detectors. |
| E0 data audit | Inspect available Unraveled sources, stage support, timestamps, potential linkage, and campaign independence | Actual local-data audit completed; **HOLD_DATA_CONTRACT**. |
| E1 edge-information experiment | MLP versus GIN with real, rewired, or self-only edges | Development engine; synthetic qualification, no new real-data efficacy result. |
| E2 degradation experiment | Paired fixed-model replay with missing/delayed graph edges and relation outages | Edge-only perturbations; full source/feature loss is not implemented. |
| E3 routing experiment | Static and learned quality policies against fixed/simple controls | Saved-prediction selection; cost proxies do not demonstrate deployed compute savings. |
| E4 frozen transfer replay | Apply frozen models and policy to separate confirmation files | Software path only; real confirmation is not released or registered. |

The E0-E4 sequence is the **telemetry-quality routing program** in the second attachment. It does not silently stand in for experiments on all three topics in the first attachment.

## Current finding

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
- [Software qualification](results/qualification_20260919/README.md): **32 tests passed**, plus the complete synthetic E1-E4 command-line run; [machine-readable receipt](results/qualification_20260919/QUALIFICATION.json).

The literature audit corrects several supplied premises. OCR-APT already reports local-model comparisons; PIDSMaker already studies instability; dataset availability and label validity still require verification. These are reasons to narrow the contribution, not to rename existing methods as new.

## Run the software

Use Python 3.11+; E0 and status use the standard library. E1-E4 qualification also requires the packages in `requirements.txt`. Use a dedicated virtual environment. All output paths below must be new; scientific receipts are never overwritten.

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

### Registration and later real-data execution

The registration command accepts only exact committed code/config/contract bytes. A new registered configuration is needed after any operative change.

```powershell
python experiments/apt_final/run.py register --output "C:/w/apt_development_registration.json"
```

It records a **development configuration freeze**, not a completed confirmatory preregistration. The initial E4 margin, verified exposure, independent units, and data-release adapter are not ready. Only after those gates are resolved should a separate real-data run use `run --stage E1` with registered configuration, normalized rows/edges, and a verified E0 receipt. Run `--help` for complete stage arguments. E2 and E3 bind upstream artifacts; E4 requires an additional policy-bound readiness receipt and compatible separate confirmation files.

## What must happen next

1. Complete the campaign/identity/time/link review packet under `data/`, grounded in author documentation or independently checked annotations.
2. Normalize and validate a small supported data subset; qualify a release adapter and freeze its hashes. If independent campaigns or joins cannot be supported, evaluate a separately audited DARPA/OpTC release and narrow the target accordingly.
3. Measure whether real graph edges add useful information before running a large architecture or routing sweep.
4. Register actual operational alert limits and exposure, qualified statistical comparisons, and the untouched confirmation design before making deployment or transfer claims.

Nothing has been sent to dataset authors. No AWS instance or paid model API was used in this branch setup. Original research results remain unchanged.
