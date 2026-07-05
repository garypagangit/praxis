# D1 New Experiment Follow-On Rollup

Generated: 2026-07-05T18:28:46.751701+00:00

## Decision Table

| ID | Experiment | Status | Decision | Key result |
|---|---|---|---|---|
| `PX-049` | Agentic slopsquatting live gate | `LIVE_GATE_FAIL` | Park or redesign | Live Qwen2.5-Coder run produced zero install actions, so no unsafe-install gap existed to close. |
| `PX-050` | Adaptive deterministic agent defenses | `LIVE_ADAPTIVE_GATE_PASS` | Continue / positive gate | Live Qwen2.5-Coder scale-up: 98 generated commands; hardened invalid recall 1.0000; hardened escape 0.0000; valid clean allow 0.9167. |
| `PX-051` | Security-utility Pareto gate | `PARETO_GATE_PASS` | Continue / positive gate | Risk-adaptive policy on Pareto front: True. |
| `PX-052` | Provenance-aware tool-boundary retrofit | `PROVENANCE_GATE_PASS` | Continue / positive gate | Alert recall 1.0000; clean FPR 0.0000. |
| `PX-053` | Approval fatigue vs. security simulation | `SIMULATION_GATE_FAIL` | Do not promote | Risk-scored compromise 0.0636. |
| `PX-054` | Refusal geometry across recurrent depth | `ACTIVATION_GATE_PASS` | Continue / positive gate | Activation capture 1.0000; cross-depth direction stability 0.8321; benign-control FPR 0.0000. |

## Bottom Line

The new D1 branch has four continue-worthy positive gates: PX-050, PX-051, PX-052, and PX-054. PX-050 is now the strongest D1 lane because it passed both a fixed adaptive-command fixture and a live model-generated adaptive scale-up. PX-053 is useful as a simulation/design result but still needs real user-study protocol before it can support human-factors claims. PX-049 should be parked as a negative live-agent result unless the agent harness is redesigned to produce real install actions.
