# 010 D0 executable mechanism screen

This directory implements the [unchanged prospective D0 protocol](../010_development_20260915/D0_PROTOCOL.md). The branch was opened on September 15; executable preparation and launch work continued on September 16, 2026. Preparation and synthetic test passes are not model results.

## Scope

The one-shot screen measures whether perturbing one artificial channel harms forecasts of two unchanged channels, and whether clipping or smoothing is sufficient. It assigns 1,024 pipeline evaluations: 32 contexts, four pipelines, six perturbations, a clean reference and a clean repeat. Independent forecasting processes channels separately, so actual forward calls and sequence counts are also recorded.

The scientific thresholds, dataset, seed, contexts, perturbations and model revisions are fixed by the earlier protocol. [Runtime interpretations](RUNTIME_INTERPRETATION.md) resolve technical details before pretrained inference. `RUNTIME_FREEZE.json` binds the executable files, tests, protocol and environment by SHA-256. The source commit is recorded separately in each launch bundle to avoid a circular commit hash.

## Components

- `code/d0_worker.py`: exact input construction, source and runtime validation, native model execution, incremental observations and failure preservation.
- `code/audit_d0.py`: independent reconstruction and decision from saved arrays; does not import the worker.
- `code/test_*.py`: synthetic correctness, adversarial provenance and mocked cloud-control checks. The source-bound worker test exercises the pinned native decode with synthetic tensors, without loading pretrained weights.
- `code/prepare_cloud_assets.py`: pinned public source/data verification and pinned checkpoint acquisition; no inference.
- `code/run_cloud.sh`: isolated inference and audit, partial-result archive, bounded persistent EBS evidence fallback, upload and guest shutdown.
- `code/cloud_d0.py` and `code/launch_d0.py`: one-attempt control of the existing designated host, external stop schedule, private receipts and archive retrieval.

## Execution and evidence

Before launch, commit the worker and runtime freeze, pass the local preparation audit and tests, and verify the existing AWS account, stopped host, stop-role permissions and rate. Operational account settings and transfer locations remain outside Git.

The authorized envelope is one existing `g5.xlarge`, 30 minutes total and a $10 combined reserve. Processing ends by minute 22; an external stop schedule is set for minute 26, leaving a shutdown margin. The shell uses an earlier fixed deadline that reserves command-delivery and shutdown time; the worker additionally reserves 160 seconds before that shell deadline for auditing and archiving. Cold installation, source tests and model loading consume that same allowance. No outcome-driven retry, new dataset or increased limit is permitted. If setup consumes the allowance, retain the failure.

Example using private paths:

```text
python code/launch_d0.py --settings PRIVATE/settings.json --bundle PRIVATE/bundle.tar.gz --bundle-sha256 SHA256 --protocol ../010_development_20260915/D0_PROTOCOL.md --freeze RUNTIME_FREEZE.json
```

The controller retrieves the archive and verifies its SHA-256. Repeat the independent audit locally using NumPy 2.2.6 and the pinned CSV/source ZIP. Publish the raw derived input/forecast arrays, all assigned evaluation identities, audit, runtime receipt and stopped-state/cost summary together. Incomplete or invalid execution is an operational HOLD. There is no scientific result until those artifacts exist and pass independent review.

## Interpretation and notices

This is development work on overlapping contexts from one previously inspected public series. It is neither an independent cyberattack replication nor a test of a novel defense. The strongest positive conclusion is eligibility to design a separate D1; negative and technical outcomes remain reportable.

Preserve the [NAB/TSB-AD notices and licenses](../010_attack_aware_forecasting/completed_qualification/licenses/NOTICE.md). Source and model identities are in the original protocol. TimesFM 3 checkpoint use remains subject to its noncommercial/nonproduction terms; weights are not included in Git or result archives. No HAI data is accessed.
