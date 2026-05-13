# Cloud Handoff

Updated: 2026-05-13

Use this file when a fresh cloud Codex run, AWS instance, or another machine needs to remember what happened locally.

## Core Rule

A cloud run only knows what it can read from the checked-out repo, an attached bundle, or a remote artifact store such as S3. It does not inherit this local OneDrive workspace, local `runs/`, local `data/`, checkpoints, or the previous Codex chat unless those details are written into versioned files or passed in the new prompt.

For this project, the lightweight source of truth is:

- `reports/EXPERIMENT_FINAL_EVALUATION_20260511.md`
- `reports/EXPERIMENT_DASHBOARD.md`
- `configs/experiment_cloud_handoff_registry.json`
- `configs/dataset_registry.json`
- `configs/detector_zoo_registry.json`
- experiment-specific reports under `reports/`
- runnable entrypoints under `scripts/`, `src/`, and `cloud_jobs/`

Heavy or private artifacts stay out of Git:

- `data/`
- `runs/`
- `outputs/`
- `artifacts/`
- `checkpoints/`
- `external/`
- model weight files such as `*.pt`, `*.pth`, `*.ckpt`, `*.safetensors`

Those must be synced to S3, copied deliberately, or regenerated.

## One-Minute Startup For Cloud

When launching a new cloud run from the bottom selector, start with this instruction:

```text
This is a fresh cloud run for the Praxis APT experiment repo. First read CLOUD_HANDOFF.md, configs/experiment_cloud_handoff_registry.json, reports/EXPERIMENT_FINAL_EVALUATION_20260511.md, reports/EXPERIMENT_DASHBOARD.md, and configs/dataset_registry.json. Treat local data/runs/checkpoints as absent unless fetched from the S3 prefixes in the registries. Preserve negative results. Do not move thresholds after seeing results. Continue only the experiment id I specify.
```

Then give the experiment id, for example:

```text
Continue experiment id tta-streaming-apt. Rehydrate only the needed inputs/artifacts, verify the locked result package, and prepare the next paper-packaging step.
```

## Past Experiment Rehydration

For any past experiment:

1. Checkout the pushed branch or commit that contains the handoff files.
2. Read `configs/experiment_cloud_handoff_registry.json`.
3. Find the experiment by `id`.
4. Read every `lightweight_evidence_paths` entry that exists.
5. Fetch only the required remote artifacts from `cloud_artifact_prefixes`.
6. Treat missing local `runs/` paths as expected unless the registry says the run must be locally present.
7. Preserve the recorded posture. A negative, hold, blocked, or shelved experiment should not be rescued by changing thresholds after the fact.

Good cloud behavior is to say, "the repo has the summary and the S3 prefix, but the heavy run output is not currently mounted," rather than to infer a result from missing files.

## Future Experiment Contract

Every new experiment should add or update four lightweight items before any expensive cloud run:

1. A stable experiment id, such as `concept-drift-optc-window-gate`.
2. A manifest copied from `templates/experiment_handoff_manifest.template.json`.
3. A short report under `reports/<experiment_id>/`.
4. A registry entry in `configs/experiment_cloud_handoff_registry.json`.

The manifest must answer:

- What hypothesis is being tested?
- What exact config/script/command runs it?
- What data paths and S3 prefixes are required?
- What metrics and stop conditions decide positive, negative, hold, or blocked?
- Where will heavy artifacts be stored?
- Which small reports, tables, and figures must be committed?

## Commit Versus Sync

Commit lightweight memory:

```powershell
git add CLOUD_HANDOFF.md templates configs reports scripts src tests cloud_jobs
git status --short
```

Before committing, review the status and remove anything that is too large, private, or generated-only.

Sync heavy memory to S3 or another artifact store:

```powershell
aws s3 sync runs/<run_id>/ s3://praxis-garypagan-272615233626-us-east-1/experiments/<experiment_id>/runs/<run_id>/
aws s3 sync outputs/<run_id>/ s3://praxis-garypagan-272615233626-us-east-1/experiments/<experiment_id>/outputs/<run_id>/
```

After sync, record the S3 prefix in the registry and summarize the result in `reports/<experiment_id>/`.

## Pre-Cloud Checklist

Run this before switching to a cloud run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_cloud_handoff_state.ps1
```

If your terminal is not already in the repo root, either move there first:

```powershell
Set-Location "C:\Users\garyp\OneDrive\Documents\codex"
powershell -ExecutionPolicy Bypass -File .\scripts\check_cloud_handoff_state.ps1
```

Or run it by absolute path:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\garyp\OneDrive\Documents\codex\scripts\check_cloud_handoff_state.ps1"
```

Then make sure:

- the branch is pushed
- the handoff files are committed or attached
- the target experiment id exists in `configs/experiment_cloud_handoff_registry.json`
- raw data and heavy run artifacts are available remotely or intentionally regenerated
- the cloud startup prompt names the exact experiment id

## Current Scientific Center

The current defense-ready answer is narrow:

- Lead positive: `tta-streaming-apt`
- Main paper path: Praxis 06 around TTA for streaming APT detection
- Architecture second track: provenance windows and detector zoo, but still label-blocked for supervised claims
- Preserved negatives: Praxis 04 stage routing, Plan 02 class imbalance, MIA shadow protocol, SEC-LoRD current seeding strategy, and several graph/provenance first gates

This is intentional. The cloud handoff should keep the portfolio honest, not make every old run look alive again.
