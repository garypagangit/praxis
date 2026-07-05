# D1 New Experiment Follow-On Rollup

Generated: 2026-07-05T18:28:46.751701+00:00

## Decision Table

| ID | Experiment | Status | Decision | Key result |
|---|---|---|---|---|
| `PX-049` | Agentic slopsquatting live gate | `LIVE_GATE_FAIL` | Park or redesign | Live Qwen2.5-Coder run produced zero install actions, so no unsafe-install gap existed to close. |
| `PX-050` | Adaptive deterministic agent defenses | `ROBUSTNESS_REPLICATION_PASS_UPLIFT_MIXED` | Continue / bounded positive | Qwen and DeepSeek live corpus: 196 generated commands; aggregate hardened escape 0.0000; valid clean allow 0.9583; registry-uplift mixed because DeepSeek generated easier direct invalid commands. |
| `PX-051` | Security-utility Pareto gate | `LIVE_POLICY_REFRESH_PASS` | Continue / positive gate | Combined live corpus: hardened policy on Pareto front, invalid escape 0.0000, utility 0.9583. |
| `PX-052` | Provenance-aware tool-boundary retrofit | `LIVE_PROVENANCE_REFRESH_PASS` | Continue / positive gate | Combined live corpus: alert recall 1.0000; clean FPR 0.0000; trace completeness 1.0000. |
| `PX-053` | Approval fatigue vs. security simulation | `SIMULATION_GATE_FAIL` | Do not promote | Risk-scored compromise 0.0636. |
| `PX-054` | Refusal geometry across recurrent depth | `ACTIVATION_GATE_PASS` | Continue / positive gate | Activation capture 1.0000; cross-depth direction stability 0.8321; benign-control FPR 0.0000. |

## Bottom Line

The new D1 branch has four continue-worthy gates: PX-050, PX-051, PX-052, and PX-054. PX-050 is still the strongest D1 lane, but the honest claim is bounded: hardened zero-escape robustness replicated across Qwen and DeepSeek, while the differential registry-uplift effect was model-dependent. PX-053 is useful as a simulation/design result but still needs real user-study protocol before it can support human-factors claims. PX-049 should be parked as a negative live-agent result unless the agent harness is redesigned to produce real install actions.
