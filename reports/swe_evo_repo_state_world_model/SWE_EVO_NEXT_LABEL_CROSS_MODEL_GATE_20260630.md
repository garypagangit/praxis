# PX-033 SWE-EVO Next-Label Cross-Model Gate

Generated: 2026-06-30T11:41:18.366297+00:00

Status: **NEXT-LABEL QUEUE READY - CROSS-MODEL EXECUTION NOT RUN IN THIS SHELL**

## Claim Boundary

This gate does not add executable SWE-EVO labels. It uses the existing 5 valid glm-4p5 execution labels plus released cross-model patch-overlap proxies to decide whether another paid/containerized cross-model slice is justified.

Patch overlap is not correctness. Any apparent threshold result below is a screening signal only until the queued model patches are executed in the benchmark images.

## Baseline

- Valid executable glm labels: `5` (`2` PASS / `3` FAIL).
- Metadata-only baseline `repo == psf/requests`: accuracy `0.8000`, F1 `0.8000`.

## Cross-Model Proxy Screen

| Model | Best threshold | Best acc | Best F1 | Acc @ F1>=0.05 | Mean file F1 | Note |
|---|---:|---:|---:|---:|---:|---|
| `deepseek-r1-0528` | `0.0500` | `1.0000` | `1.0000` | `1.0000` | `0.1300` | post-hoc beats metadata |
| `gpt-4o-2024-11-20` | `0.0500` | `1.0000` | `1.0000` | `1.0000` | `0.1500` | post-hoc beats metadata |
| `gpt-4.1-2025-04-14` | `0.0500` | `0.8000` | `0.8000` | `0.8000` | `0.4200` | does not beat metadata |
| `gpt-5-nano-2025-08-07` | `0.0500` | `0.8000` | `0.6667` | `0.8000` | `0.0800` | does not beat metadata |
| `kimi-k2-instruct` | `0.0500` | `0.6000` | `0.6667` | `0.6000` | `0.5222` | does not beat metadata |
| `o3-2025-04-16` | `0.0500` | `0.6000` | `0.6667` | `0.6000` | `0.2844` | does not beat metadata |

Two released-prediction models (`gpt-4o-2024-11-20` and `deepseek-r1-0528`) separate the five glm labels perfectly at a tiny file-overlap threshold, but this is post-hoc on five examples. It justifies a small cross-model execution queue; it does not prove a repo-state world model.

## Next Executable Label Queue

| Priority | Lane | Model | Instance | Proxy expected | glm label | File F1 | Purpose |
|---:|---|---|---|---|---|---:|---|
| 1 | primary | `gpt-4o-2024-11-20` | `iterative__dvc_0.30.0_0.30.1` | `FAIL` | `FAIL` | `0.0000` | cross-model negative control |
| 2 | primary | `gpt-4o-2024-11-20` | `iterative__dvc_2.21.1_2.21.2` | `FAIL` | `FAIL` | `0.0000` | cross-model negative control |
| 3 | primary | `gpt-4o-2024-11-20` | `psf__requests_v2.12.2_v2.12.3` | `PASS` | `PASS` | `0.5000` | cross-model positive replication |
| 4 | primary | `gpt-4o-2024-11-20` | `psf__requests_v2.27.0_v2.27.1` | `FAIL` | `FAIL` | `0.0000` | cross-model negative control |
| 5 | primary | `gpt-4o-2024-11-20` | `psf__requests_v2.9.0_v2.9.1` | `PASS` | `PASS` | `0.2500` | cross-model positive replication |
| 6 | confirmation | `deepseek-r1-0528` | `iterative__dvc_0.30.0_0.30.1` | `FAIL` | `FAIL` | `0.0000` | cross-model negative control |
| 7 | confirmation | `deepseek-r1-0528` | `iterative__dvc_2.21.1_2.21.2` | `FAIL` | `FAIL` | `0.0000` | cross-model negative control |
| 8 | confirmation | `deepseek-r1-0528` | `psf__requests_v2.12.2_v2.12.3` | `PASS` | `PASS` | `0.4000` | cross-model positive replication |
| 9 | confirmation | `deepseek-r1-0528` | `psf__requests_v2.27.0_v2.27.1` | `FAIL` | `FAIL` | `0.0000` | cross-model negative control |
| 10 | confirmation | `deepseek-r1-0528` | `psf__requests_v2.9.0_v2.9.1` | `PASS` | `PASS` | `0.2500` | cross-model positive replication |

## Execution Availability

- Local Docker available: `False`.
- AWS credentials available in this shell: `False`.
- AWS diagnostic: `aws: [ERROR]: An error occurred (NoCredentials): Unable to locate credentials. You can configure credentials by running "aws login".`.

No cloud or Docker execution was started from this shell because the local Docker CLI is unavailable and AWS credentials are not loaded.

## Decision

Keep PX-033 as an active execution-and-prediction lane only. Run the 5-row primary `gpt-4o-2024-11-20` queue when AWS SSO is connected; add the 5-row DeepSeek confirmation queue only if the primary queue beats the metadata baseline. Do not start RWML/world-model training unless cross-model executable labels beat accuracy/F1 `0.8000` on a larger valid slice.

## Artifacts

- Raw JSON: `runs/px033-swe-evo-next-label-gate-20260630/px033_swe_evo_next_label_gate.json`
- Cross-model proxy scores: `runs/px033-swe-evo-next-label-gate-20260630/cross_model_proxy_scores.csv`
- Next-label queue: `runs/px033-swe-evo-next-label-gate-20260630/next_label_queue.csv`
- Prior executable labels: `runs/swe-evo-failure-predictor-probe-20260630/`
