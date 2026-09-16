# D0 closed: hold cross-channel-harm scale-up

**September 16, 2026 — technical audit PASS; scientific decision `HOLD_CROSS_CHANNEL_HARM_SCALE_UP`.** All 1,024 evaluations completed. The host is verified stopped, evidence is archived, and the external stop schedule was removed after shutdown.

## What the screen found

Changing channel 0 changed forecasts of unchanged channels 1 and 2. However, every raw-joint perturbation variant slightly **reduced** mean error on those protected channels. None met the registered requirement for positive mean error inflation of at least 0.02 standardized units. Consequently, zero variants qualified; the protocol required at least two.

| Raw-joint variant | Contexts with displacement at least 0.05 and above the numerical floor | Mean protected-channel error change |
|---|---:|---:|
| Step 1 | 6 / 32 | -0.007942 |
| Step 3 | 8 / 32 | -0.006084 |
| Step 6 | 11 / 32 | -0.007084 |
| Ramp 1 | 22 / 32 | -0.017816 |
| Ramp 3 | 23 / 32 | -0.013414 |
| Ramp 6 | 23 / 32 | -0.008986 |

Negative error change means lower average error. Each mean includes all 32 contexts. Some individual contexts had increased error: this is not a claim of universal robustness or absence of individual harm.

Clean point forecasts and all nine quantiles repeated exactly. The independent-channel control showed exactly zero protected-channel displacement. The numerical floor was therefore `1e-5`. Source, runtime, unchanged inputs/targets, native routing, all evaluation identities and finite outputs passed audit.

The comparison asking whether a simple preprocessing control is sufficient was **not reached**, because no raw-joint variant qualified. The machine report's empty `adequate_simple_controls` list must not be read as evidence that clipping and smoothing failed.

## Decision and portfolio consequence

- Close this fixed D0 screen as a completed negative result for its prespecified harm criterion. Retain all variants and forecasts.
- Hold 010 scale-up and D1 launch. This run does not justify replacing the dataset, windows or amplitudes to obtain a favorable result.
- Keep CTI first in the Praxis review queue: explain its bounded contribution against the closest prior work and trace one improvement and one mismatch failure. See [CTI next actions](../010_development_20260915/CTI_NEXT_ACTIONS.md).
- Retain 008 as the completed alternative for contribution/scope review. The third defensible slot remains open; 010 has not earned it through D0. PX-055 remains a bounded replication with additional spending on hold.

The series was already inspected during development. Its 32 overlapping contexts and artificial channel construction do not supply independent cyber incidents, real sensor relationships, a new defense, attack detection, retention or recovery evidence. No HAI data was accessed.

## Execution and verification

| Check | Result |
|---|---|
| Frozen source commit | `6f8b650b98b8ed9af0816f7ebc46628fe864d74c` |
| Pipeline evaluations | 1,024 / 1,024 |
| Native forward calls | 1,536 |
| Tensor batch / scalar channel sequences | 1,536 / 3,072 |
| Worker wall time | 207.83 seconds |
| Peak allocated / reserved GPU memory | 2.464 / 2.674 GiB |
| Frozen cloud worker tests | 16 passed, zero skipped |
| Frozen cloud auditor tests | 42 passed |
| Cloud and local full audit | PASS; JSON reports identical |
| Start request / stopped observation, UTC | 21:06:47 / 21:17:07 |
| Conservative elapsed-to-stopped observation | 620.57 seconds, below 30 minutes |
| Conservative compute estimate | $0.1734 at $1.006/hour |
| Estimate plus $5 incidentals allowance | $5.1734, below the $10 reserve |

The cost figure is an estimate, not an invoice. It conservatively counts the full interval through stopped-state observation, including shutdown. The $5 allowance is a budget allowance, not recorded spending. One host and one processing attempt were used. No force stop or inference rerun occurred.

The original September 15 protocol and the executable freeze remain unchanged historical records. This outcome supplies their completed status.

## Evidence

- [Full audited measurements](completed_run/audit/RESULTS.md), [cloud audit JSON](completed_run/audit/AUDIT.json), and [matching local audit](local_audit/AUDIT.json).
- [Raw forecasts and quantiles](completed_run/run/forecasts.npz), [exact derived inputs and targets](completed_run/run/inputs.npz), and [all evaluation observations](completed_run/run/observations.jsonl).
- [Runtime and source receipt](completed_run/run/RUN_RECEIPT.json), [source commit](completed_run/SOURCE_COMMIT.json), and [frozen execution configuration](RUNTIME_FREEZE.json).
- [Evidence hashes](EVIDENCE_MANIFEST.json), [shutdown receipt](SHUTDOWN.json), [operational closeout](EXECUTION_SUMMARY.json), and [independent review](INDEPENDENT_REVIEW.json).

Original archive SHA-256: `119ed5a294260acb2ce188a721e23759a49e778a357c9a44af66f564ffc20e36`. The early review download and final controller download had the same verified hash. Model weights and private operational settings are excluded from Git. The [existing data notices](../010_attack_aware_forecasting/completed_qualification/licenses/NOTICE.md) apply to the derived evidence.
