# PX-053 Approval Fatigue vs. Security Simulation Gate

Generated: 2026-07-05T18:28:46.738638+00:00

## Status

**SIMULATION_GATE_FAIL**

This is a synthetic simulation only. It is useful for deciding whether approval routing is worth prototyping, but it is not human-subject evidence and should not be described as measured user behavior.

## Policy Scores

| Policy | Sessions | Compromise rate | Completion rate | Prompts/session | Prompts/action |
|---|---:|---:|---:|---:|---:|
| `approve_all` | `10000` | `0.2878` | `0.9235` | `0.0000` | `0.0000` |
| `every_action_approval` | `10000` | `0.0608` | `0.6525` | `6.0121` | `1.0000` |
| `high_risk_only` | `10000` | `0.1756` | `0.8977` | `1.0884` | `0.1808` |
| `risk_scored_routing` | `10000` | `0.0636` | `0.8919` | `1.3884` | `0.2309` |

## Gate Checks

| Check | Pass |
|---|---:|
| `sessions_at_least_10000` | `PASS` |
| `risk_scored_compromise_below_every_action` | `FAIL` |
| `prompt_reduction_vs_every_action_at_least_0_30` | `PASS` |
| `risk_scored_completion_at_least_0_90` | `FAIL` |

## Interpretation

PX-053 does not clear even the simulation gate. It should be abandoned or redesigned before any user-study effort.

## Artifacts

- `policy_simulation_scores.csv`: policy-level simulation scores.
- `summary.json`: machine-readable metrics and checks.
