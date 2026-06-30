# PX-023 PIDSMaker Larger-Hidden-State Pivot Gate

Generated: 2026-06-30T11:37:07.614686+00:00

Status: **PIVOT SCAFFOLD PASS - NO POSITIVE SAE RESULT YET**

## Claim Boundary

MAGIC/CADETS Phase A remains a failed SAE interpretability result. This gate only tests whether the one allowed larger-hidden-state PIDSMaker pivot has a mechanically credible activation-export path before spending GPU time on a real detector run.

The NodLink smoke below uses synthetic graph features and an untrained encoder. It proves interface compatibility only; it is not evidence that real PIDSMaker activations are interpretable.

## Prior MAGIC Phase A Result

| Check | Value | Threshold | Pass? |
|---|---:|---:|---|
| mse_ratio | `0.000022` | `0.2500` | yes |
| feature_death_rate | `0.911914` | `0.5000` | no |
| seed_stability | `0.281500` | `0.3000` | no |

## PIDSMaker Candidate Matrix

| System | Encoder methods | Node hidden | Node output | Decision |
|---|---|---:|---:|---|
| magic | `magic_gat` | `64` | `64` | failed_predecessor |
| orthrus | `tgn,graph_attention` | `128` | `64` | hook_only_secondary |
| nodlink | `sum_aggregation` | `256` | `256` | preferred_direct_pivot |
| rcaid | `rcaid_gat` | `128` | `3` | reject_output_bottleneck |
| kairos | `graph_attention,tgn` | `100` | `100` | secondary_tgn_candidate |

NodLink is the only clean direct pivot in the checked configs: it exposes a 256-dimensional encoder output without a small classifier bottleneck. Orthrus and Kairos remain secondary hook/TGN candidates; R-Caid's configured 3-dimensional output is rejected for this SAE use.

## NodLink Smoke

- Activation export: `512` rows x `256` dimensions.
- Cache validation: valid=`True`, std=`0.3307`, nonzero fraction=`1.0000`.
- Tiny non-research TopK SAE smoke: mean MSE ratio `0.2643`, mean feature-death rate `0.1064` across two seeds.

## Decision

Do not reopen MAGIC or proceed to Phase B. Keep PX-023 as a single active pivot gate only if the next step is a real NodLink activation export followed by the frozen Phase A SAE diagnostics. If that real NodLink export fails feature death or stability, close PX-023 as a negative result for provenance-graph detector hidden-state SAEs.

## Artifacts

- Raw JSON: `runs/px023-pidsmaker-pivot-gate-20260630/px023_pidsmaker_pivot_gate.json`
- Candidate matrix CSV: `runs/px023-pidsmaker-pivot-gate-20260630/candidate_matrix.csv`
- Synthetic activation cache and tiny SAE smoke: `runs/px023-pidsmaker-pivot-gate-20260630/`
- Prior MAGIC evidence: `reports/praxis05_phase_a/FULL_GPU_PHASE_A_20260510.md` and `runs/praxis05-phase-a-full-magic-aws-20260510/diagnostics.json`
