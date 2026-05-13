# Praxis 05 Full GPU Phase A

Generated: 2026-05-10

## Decision

Gate result: `FAIL - PHASE A KILL SWITCH TRIPPED`

The full preregistered MAGIC/CADETS SAE Phase A was run on AWS GPU using the frozen 5-seed, 4096-feature, 20,000-step config. It confirms the local warning: the SAE reconstructs MAGIC activations extremely well, but most features remain dead and seed stability is slightly below threshold. Do not proceed to Phase B.

## Cloud Run

| Field | Value |
|---|---|
| SSM command | `da81dd5d-96ab-43f1-b35c-e972cd216e7a` |
| Instance | `i-039ed976444ade397` / `g5.xlarge` |
| S3 output | `s3://praxis-garypagan-272615233626-us-east-1/experiments/praxis05/cloud_jobs/praxis05-phase-a-full-magic-20260510/output/` |
| Local output | `runs/praxis05-phase-a-full-magic-aws-20260510/` |
| Activation cache | `1,269,862 x 64` MAGIC CADETS train activations |
| Config | `configs/praxis05-sae-topk-k32-x16.json` |

## Kill-Switch Checks

| Check | Value | Threshold | Pass |
|---|---:|---:|---|
| MSE ratio | `0.0000224` | `<= 0.25` | yes |
| Feature death rate | `0.9119` | `< 0.50` | no |
| Seed stability | `0.2815` | `>= 0.30` | no |

## Per-Seed Metrics

| Seed | MSE ratio | Feature death rate | Reconstruction MSE | Elapsed seconds |
|---:|---:|---:|---:|---:|
| 13 | `0.0000242` | `0.9111` | `0.00000129` | `278.7` |
| 42 | `0.0000230` | `0.9116` | `0.00000123` | `276.2` |
| 137 | `0.0000217` | `0.9141` | `0.00000116` | `274.5` |
| 271 | `0.0000209` | `0.9126` | `0.00000112` | `274.9` |
| 1729 | `0.0000224` | `0.9102` | `0.00000120` | `274.8` |

## Interpretation

- The result is not an infrastructure failure. All five seeds completed and diagnostics ran.
- Reconstruction is almost too good: the 64-dimensional MAGIC representation can be reconstructed with a small active subset of the 4096 SAE features.
- The feature-death failure is stable across all five seeds, so raising the threshold would be post-hoc threshold moving.
- The correct next step is either the one allowed PIDSMaker pivot to a larger-hidden-state detector or a negative-result note arguing that MAGIC CADETS hidden states are too compressed for useful TopK SAE decomposition.

## PIDSMaker Pivot Status

PIDSMaker is present locally at `external/PIDSMaker`, commit `216df3aaf76224c0a9311e66ae2110fd8d3730d7`, and it exposes larger-hidden-state systems such as Orthrus (`node_hid_dim: 128`), NodLink (`256`), Kairos (`100`), and R-Caid (`128`). The pivot is not a direct reuse of the MAGIC activation cache. It requires running a PIDSMaker system through its own dataset/database pipeline, then adding a hook/export path for hidden states before rerunning the SAE gate.

Next concrete action: build a PIDSMaker activation-export scaffold for one larger-hidden-state system, preferably Orthrus or NodLink, and run a smoke export before committing GPU time.
