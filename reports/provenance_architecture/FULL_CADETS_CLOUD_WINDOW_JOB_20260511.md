# Full Cadets Cloud Window Job

Generated: 2026-05-11 local / 2026-05-12 UTC

## Status

Status: **COMPLETE - DETECTOR CLAIM STILL BLOCKED**.

The full E5 Cadets provenance window factory job was launched on the AWS data-loader instance:

| Field | Value |
|---|---|
| Instance | `i-0bd262c42220bb4a2` |
| Instance name | `praxis-data-loader` |
| Region | `us-east-1` |
| Input path | `/mnt/praxis/datasets/darpa-tc/e5/cadets` |
| Input scope | `49` gzip Avro chunks visible locally, backed by the `13.0 GiB` S3 mirror |
| Node labels | PIDSMaker `E5-CADETS` node labels, `node_Nginx_Drakon_APT.csv` and `node_Nginx_Drakon_APT_17.csv` |
| Events per window | `50,000` |
| S3 output | `s3://praxis-garypagan-272615233626-us-east-1/experiments/provenance-window-factory/runs/full-e5cadets-20260511/` |

## Completion Result

The cloud worker completed and synced five artifacts to S3 at `2026-05-12T05:22:37Z`.

| Metric | Value |
|---|---:|
| Source files | `49` |
| Edge rows | `480,537,673` |
| Windows | `9,611` |
| Timestamp span seconds | `371,328.882` |
| Node-label rows | `124` |
| Attack-touch windows | `9,609` |
| Benign-or-unlabeled windows | `2` |

## Artifacts

| Artifact | Location |
|---|---|
| Local run directory | `runs/full-e5cadets-window-factory-20260511/` |
| Full window-factory report | `reports/provenance_architecture/FULL_CADETS_WINDOW_FACTORY_20260511.md` |
| Detector-zoo gate report | `reports/provenance_architecture/PROVENANCE_DETECTOR_ZOO_GATE_FULL_E5CADETS_20260511.md` |
| Density diagnostic | `reports/provenance_architecture/CADETS_ATTACK_TOUCH_DENSITY_DIAGNOSTIC_20260512.md` |
| S3 output | `s3://praxis-garypagan-272615233626-us-east-1/experiments/provenance-window-factory/runs/full-e5cadets-20260511/` |

## Commands

Fetch results and rerun the detector-zoo gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\fetch_full_cadets_window_results.ps1
```

## Honest Interpretation

The full stream proves the parser and architecture scale, but it does not unlock supervised detector claims. PIDSMaker node-touch labels are too broad on this stream: only `2` windows remain benign-or-unlabeled. The detector-zoo gate correctly refused to train.
