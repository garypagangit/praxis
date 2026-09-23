# AWS acquisition and compute status

**Final status, September 23, 2026: the ProvICS subset was downloaded successfully on AWS, retrieved and verified locally, and the designated worker is stopped.** No model was fitted in these acquisition allocations; the instance is GPU capable, but this job used its CPU and network.

The user completed the normal AWS SSO sign-in. [Initial expired-session evidence](aws_readiness.json) and the later [authenticated inventory](aws_authenticated_readiness.json) remain separate historical receipts.

## Completed attempts

| Attempt | Frozen source | Actual outcome | Estimated compute* | Stop verified |
|---|---|---|---:|---|
| [1](PROVICS_ATTEMPT1_RESULT.json) | `b777e84` | Existing Python environments lacked pandas; no dataset request. | $0.08959 | Yes |
| [2](PROVICS_ATTEMPT2_RESULT.json) | `154beed` | Original run filesystem had less than the required 2 GB free; no dependency installation or dataset request. | $0.09206 | Yes |
| [3](PROVICS_ATTEMPT3_RESULT.json) | `830da43` | Selected an already mounted filesystem with sufficient measured free space, used an isolated environment, and acquired all seven pinned source files. | $0.55094 | Yes |

*These are conservative estimates from instance-start request to the first recorded observation of stopped state, using $1.006/hour. They are not invoices. The final estimate includes a network interruption that delayed stop verification after a successful stop request. Their sum is approximately **$0.73259 compute**. Each allocation also reserved $0.75 for incidental charges; a reserve is not measured spending.

The final worker ran from 13:55:43 to 13:56:01 UTC. Stop was requested at 13:56:16 UTC and verified by the controller at 14:27:57 UTC. Ordinary AWS role-credential endpoint connections temporarily failed between those checks. The independent watchdog stayed enabled during the interruption and was deleted only after stopped-state verification. No additional worker was launched to recover results.

## Reproducible output

- **Author revision:** `18b4b0e1359d3d02347301c55f97c3d98f5dab5c` for all seven files.
- **Acquired source bytes:** 29,308,373; every local file hash matches its acquisition receipt.
- **Private result archive:** 7,536,909 bytes; SHA-256 `6a724dd67f7d90daa3df354613972ce94490c2fc635427bb260f2378d2a2339e`.
- **Public metadata:** [qualification results](../data_qualification/results/provics_cloud_attempt3/provics_qualification.json), [byte and clock audit](../data_qualification/results/provics_cloud_attempt3/measurement_support.json), and [final compute receipt](PROVICS_ATTEMPT3_RESULT.json).
- **Private local raw data:** `C:/w/apt_benchmark_data_20260920/praxis_next/cloud_provics_attempt3/collected/outputs/data/provics`.

The worker used an existing writable mount at `/opt/dlami/nvme` after measuring available space. It did not mount or format storage, remove shared data, create instances or volumes, or touch the shared running data-loader. The frozen [protocol](PROVICS_CLOUD_PROTOCOL.md) bounded the worker to 30 minutes and independent stop request to 40 minutes, with a 45-minute outer ceiling and $2 reserve per allocation.

## Scientific status

Acquisition succeeded; model validation has not occurred on this dataset. The physical subset supports a possible ICS process-history study after a target and time split are frozen. It does not by itself establish completed lateral movement, successful exfiltration, collection cost, or logging delay. See the [data qualification decision](../data_qualification/README.md).
