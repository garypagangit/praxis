# Python code-pair qualification

This package audits and qualifies the 164 public HumanEvalPack Python canonical/buggy pairs against original HumanEvalPack tests and HumanEval+ v0.1.10 inputs. Read `QUALIFICATION_PROTOCOL.md` before execution. Qualification is a prerequisite for a separately frozen policy experiment.

Preparation performs public downloads, hashes, JSON/Parquet parsing, and AST inspection only. It does not execute released programs. All 164 task IDs and callable signatures align. The frozen input pool contains 123,981 unique structural inputs: 32,090 tool inputs and 91,891 reserved outcomes. Raw input occurrences, duplicates, example-extraction coverage, and source differences remain in `TASK_IDENTITY.json`.

## Prepare and transfer

On the preparation machine:

```powershell
.venv/Scripts/python.exe C:/w/fp008/final_praxis/008_independent_evidence_audit/code_study/qualification/fetch_prepare.py --private-dir reports/praxis_20260914_code_study
```

Add `--offline` after the first verified download. Fixed dataset SHA256 values and Git blob checks reject changed artifacts. The command produces the private `praxis008-code-qualification.tar.gz`, an unpacked `bundle/`, and `BUNDLE_RECEIPT.json`. Raw code, tests, inputs, and third-party evaluation source stay in that private bundle. Public metadata contains no program or test-input payloads.

## Build and execute in AWS Linux

Extract the bundle into an otherwise empty directory on encrypted scratch. Record the pulled Python base image digest and resulting image ID before execution:

```bash
docker pull python:3.11.9-slim-bookworm
docker image inspect python:3.11.9-slim-bookworm > python-image-receipt.json
docker build -f qualification/Dockerfile -t praxis008-qualification:FROZEN_REVISION .
docker image inspect praxis008-qualification:FROZEN_REVISION > qualification-image-receipt.json
bash qualification/run_docker.sh praxis008-qualification:FROZEN_REVISION "$PWD" /ENCRYPTED_SCRATCH/pilot pilot
```

The wrapper creates a nonroot, network-none, read-only Docker container with no credential mounts, no effective capabilities, no-new-privileges, three CPUs, 12 GiB memory, bounded PIDs, and a six-hour outer timeout. The runtime independently rejects Windows, UID 0, unexpected network interfaces, AWS environment variables, missing no-new-privileges, or effective Linux capabilities. Host image construction may access official package services before any code workload starts.

After reviewing the separate pilot result and controls, use a new result directory and `full` as the final argument. This assigns all 164 tasks. The exact same artifact image, data, comparator, limits, and split must be retained. Pilot membership is the first eight development IDs under the frozen hash ranking; no output-dependent pilot selection is allowed.

Within each task, a reference worker computes expected outputs from the separately released EvalPlus canonical code, then separate HumanEvalPack canonical and buggy workers run. Each process loads a fresh program namespace, copies inputs, fixes random seeds, and records per-input outcomes. The `find_zero` residual predicate follows the pinned current evaluator. The original test module's own trailing `check(entry_point)` is executed exactly once. Assertion tracing preserves lazy failure-message evaluation and stops at the first failure. No missing result falls back to another implementation.

## Results and resumption

- `PROGRESS.json` records completed task chains during the run.
- `public/SUMMARY.json` reports qualification thresholds and limitations.
- `public/TASK_RESULTS.json` retains all 164 IDs, original-suite assertion traces, augmented counts, and exclusion reasons.
- `public/CASES.jsonl.gz` records every assigned variant/input ID, split, status, time limit, and execution time. Expected values are omitted.
- `public/RECEIPT.json` hashes the public results and frozen scripts.
- `private/` contains task payloads, reference expected values, per-worker logs, and immutable numbered attempts. Do not publish it.

An interrupted run can resume using the same frozen configuration and result directory. Completed matching attempts are reused; incomplete attempts are retained and a new numbered attempt is created. Missing/censored cases remain explicit in normalization. A different bundle/configuration is rejected for that directory.

Exit 0 means the assigned run completed; the scientific eligibility/feasibility decision is in `SUMMARY.json`. Pilot completion does not authorize a policy inference claim. Every full-run task remains in the denominator, including infrastructure errors, runtime failures, and ineligible pairs.

## Published source-only metadata

`SOURCE_MANIFEST.json` records source pins and bytes/hashes; `TASK_IDENTITY.json` records ID/signature audits; `SPLIT_MANIFEST.json` records task split/seed and input-assignment checksums; `INPUT_SPLITS.jsonl.gz` contains per-input fingerprint assignments without input values; `PREPARATION_SUMMARY.json` reports parsing counts. The verifier and runtime scripts are original work, and third-party licenses accompany the private execution bundle.
