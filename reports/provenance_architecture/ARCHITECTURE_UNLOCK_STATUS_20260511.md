# Architecture Unlock Status

Generated: 2026-05-11

## Bottom Line

Two shared architecture pieces are now in place:

1. A provenance window factory that turns normalized Cadets edge JSONL into chronological window metadata, fixed-width detector features, a manifest, and a label template.
2. A detector-zoo registry with four sklearn-compatible baseline families: logistic regression, random forest, extra trees, and a small MLP.

This does not create a new positive scientific claim. It removes duplicated plumbing and makes the next graph/drift/watermark/privacy experiments easier to run honestly.

## Smoke Result

| Component | Evidence | Smoke result | Limitation |
|---|---|---|---|
| Provenance window factory | `reports/provenance_architecture/PROVENANCE_WINDOW_FACTORY_20260511.md` | Converted `98,862` Cadets edges into `20` chronological windows with `29` event features and `32` exec features | Current sample has `0` labeled windows, one source file, and only `245.329` seconds |
| PIDSMaker node-label attachment | `reports/provenance_architecture/PROVENANCE_WINDOW_FACTORY_E5CADETS_PIDSMaker_20260511.md` | Attached `126` E5-CADETS node labels; `19` of `20` windows touch known attack nodes | Labels are node-level, not stage/time-span ground truth |
| Detector-zoo gate | `reports/provenance_architecture/PROVENANCE_DETECTOR_ZOO_GATE_20260511.md` | Correctly refused to train: `19` attack-touch windows vs `1` benign/unlabeled window | Need longer stream or confirmed benign windows |
| Detector zoo registry | `reports/provenance_architecture/DETECTOR_ZOO_REGISTRY_20260511.md` | Registered and instantiated `4` baseline detector families | Registry is not a trained detector suite yet |
| Focused tests | `tests/test_provenance_window_factory.py`, `tests/test_detector_registry.py` | `4 passed` | Tests validate plumbing, not research claims |

## Cloud Full-Stream Job

The full E5 Cadets window build completed on `i-0bd262c42220bb4a2` against `/mnt/praxis/datasets/darpa-tc/e5/cadets`, using the S3-backed `13.0 GiB` Cadets mirror and the two local PIDSMaker E5-CADETS node-label files. It processed `480,537,673` edge events into `9,611` windows across `371,328.882` seconds of timestamp span. Status report: `reports/provenance_architecture/FULL_CADETS_CLOUD_WINDOW_JOB_20260511.md`. Output target:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/provenance-window-factory/runs/full-e5cadets-20260511/`

The job produced `windows.csv`, `window_features.csv`, `manifest.json`, and `report.md`. The full-stream detector-zoo gate still blocked supervised claims because PIDSMaker node-touch labels produced `9,609` attack-touch windows and only `2` benign-or-unlabeled windows.

A separate density diagnostic found enough variation for a weak-proxy task: low-touch/high-touch windows at threshold `5,000` are learnable from event/exec rates alone, with chronological Macro-F1 from `0.9704` to `0.9788` across detector-zoo members. This can prioritize windows and stress-test representations, but it is not benign-vs-attack ground truth.

## What This Opens

| Experiment family | What is now reusable | Remaining blocker |
|---|---|---|
| Concept drift on provenance detectors | Chronological windows and feature tables | Longer Cadets/OpTC streams plus labels/anomaly windows |
| Continuous-time TGN | Shared temporal windows and vocabulary | Better objective than next-event type, preferably anomaly/window labels |
| Contrastive SSL on provenance graphs | Shared window boundaries and feature vocabulary | Stronger node features and hard negatives |
| Stage routing on provenance graphs | Common window IDs and potential stage-label attachment point | Reliable stage/attack-window labels |
| Watermarking, MIA, adversarial robustness | Common detector target families | Trained detector suite with stable utility |
| Weak-proxy representation diagnostics | Full Cadets windows plus low-touch/high-touch density task | External validation before any attack-detection claim |

## What I Still Need From You

| Need | Why it matters | Can proceed without it? |
|---|---|---|
| Longer Cadets/OpTC host stream selection | Needed for defensible drift/graph claims | Full E5 Cadets processed; still need confirmed benign/attack intervals or another labeled stream |
| Attack windows, anomaly spans, or stage labels | Needed for supervised detector/stage claims | No, not for honest supervised claims |
| AWS CLI/SSO availability in the active shell | Needed to run larger cloud processing batches | Resolved for this run via `C:\Program Files\Amazon\AWSCLIV2\aws.exe` |

## Next Honest Move

Do not train a supervised detector on PIDSMaker node-touch labels alone. Next honest options are: attach confirmed attack/anomaly intervals to the full Cadets windows, process a different labeled host stream with real benign support, or use the attack-touch density diagnostic only as a clearly marked weak-proxy task.
