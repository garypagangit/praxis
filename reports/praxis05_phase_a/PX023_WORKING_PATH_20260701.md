# PX-023 Working Path

Generated: 2026-07-01

Status: **NEGATIVE NOW - REOPEN ONLY WITH REAL PIDSMaker/NodLink RUNTIME**

## Short Answer

PX-023 is not currently a positive. The only credible way to get PX-023 working is to run a real PIDSMaker NodLink detector/encoder over real E5 Cadets provenance data, export the actual 256-dimensional NodLink hidden activations, and rerun the frozen Phase A SAE diagnostics at full specification.

Do not reopen MAGIC. Do not use the proxy as a defense result. Do not move to Phase B until the real NodLink activation cache passes Phase A.

## Why It Failed So Far

The original MAGIC hidden-state SAE failed Phase A:

| Check | Value | Threshold | Result |
|---|---:|---:|---|
| MSE ratio | `0.000022` | `<= 0.2500` | pass |
| Feature-death rate | `0.911914` | `<= 0.5000` | fail |
| Seed stability | `0.281500` | `>= 0.3000` | fail |

The one allowed pivot found a better candidate: PIDSMaker NodLink exposes a clean 256-dimensional encoder output. The synthetic smoke test proved only interface compatibility.

The real-data proxy then used full E5 Cadets window features and NodLink-style activations, but it was still not a full PIDSMaker detector run. It failed the stability gate:

| Check | Value | Threshold | Result |
|---|---:|---:|---|
| MSE ratio | `0.026022` | `<= 0.2500` | pass |
| Feature-death rate | `0.260742` | `<= 0.5000` | pass |
| Seed stability | `0.173000` | `>= 0.3000` | fail |

## What Is Needed To Make PX-023 Work

1. Provision an environment with Docker and Postgres/psql, or a native PIDSMaker-compatible Postgres runtime.
2. Load the E5 Cadets provenance data into the PIDSMaker expected graph/database schema.
3. Run the actual NodLink detector/encoder over the real provenance graph, not aggregate window proxy features.
4. Hook the 256-dimensional NodLink encoder output before any classifier bottleneck.
5. Export an activation cache with row IDs, host/day/time/window provenance, labels, split metadata, and activation tensors.
6. Run frozen Phase A SAE diagnostics at full spec: `4096` SAE features, registered TopK setting such as `k=32`, `20000` GPU steps, and at least five seeds.
7. Use the same kill-switch thresholds: MSE ratio `<= 0.2500`, feature-death rate `<= 0.5000`, and seed stability `>= 0.3000`.

## Reopen Criteria

PX-023 may be reopened only if all of the following are true:

- Real PIDSMaker/NodLink runtime is installed and reproducible.
- E5 Cadets graph data loads into the expected database schema.
- The exported activations are actual NodLink encoder outputs, not window-feature proxies.
- Activation sanity checks pass: nonzero fraction, variance, shape, source IDs, and label/split integrity.
- Full Phase A passes all three thresholds across seeds.

## Close Criteria

Close PX-023 permanently for this dissertation cycle if any of these happen:

- The real PIDSMaker database/runtime cannot be built.
- NodLink activations cannot be hooked before the classifier bottleneck.
- Real NodLink activations fail feature death or seed stability under the frozen Phase A gate.
- The only available evidence remains proxy activations or synthetic smoke tests.

## Practical Recommendation

PX-023 is worth one more attempt only if the next work item is infrastructure-first: get PIDSMaker running with Postgres and real E5 Cadets graph ingestion. If that succeeds, run the real NodLink export and full Phase A. If it fails, PX-023 should stay closed as an honest negative result.

## Current Evidence

- Pivot scaffold: `reports/praxis05_phase_a/PX023_PIDSMaker_PIVOT_GATE_20260630.md`
- Real-data proxy gate: `reports/praxis05_phase_a/PX023_NODLINK_REALDATA_PROXY_GATE_20260630.md`
- Prior MAGIC Phase A: `reports/praxis05_phase_a/FULL_GPU_PHASE_A_20260510.md`
- Pivot run artifacts: `runs/px023-pidsmaker-pivot-gate-20260630/`
- Proxy run artifacts: `runs/px023-nodlink-realdata-proxy-20260630/`

