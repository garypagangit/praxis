# D1 New Experiment Follow-On Rollup

Generated: 2026-07-05T18:28:46.751701+00:00

## Decision Table

| ID | Experiment | Status | Decision | Key result |
|---|---|---|---|---|
| `PX-049` | Agentic slopsquatting live gate | `LIVE_GATE_FAIL` | Park or redesign | Live Qwen2.5-Coder run produced zero install actions, so no unsafe-install gap existed to close. |
| `PX-050` | Adaptive deterministic agent defenses | `FINAL_MANUSCRIPT_DRAFT_PUBLISHABLE_BOUNDED_POSITIVE` | Lead D1 paper candidate | Qwen and DeepSeek live corpus plus parser stress: aggregate hardened escape 0.0000 on 196 live commands; parser-stress hardened escape 0.0000 on 984 inert mutations; valid clean allow 0.9583 live and 1.0000 stress. Final manuscript draft is now written. Registry-uplift remains model-dependent. |
| `PX-051` | Security-utility Pareto gate | `LIVE_POLICY_REFRESH_PASS` | Continue / positive gate | Combined live corpus: hardened policy on Pareto front, invalid escape 0.0000, utility 0.9583. |
| `PX-052` | Provenance-aware tool-boundary retrofit | `LIVE_PROVENANCE_REFRESH_PASS` | Continue / positive gate | Combined live corpus: alert recall 1.0000; clean FPR 0.0000; trace completeness 1.0000. |
| `PX-053` | Approval fatigue vs. security simulation | `SIMULATION_GATE_FAIL` | Do not promote | Risk-scored compromise 0.0636. |
| `PX-054` | Refusal geometry across recurrent depth | `SCALE_GATE_PASS` | Bounded characterization positive | Safe Huginn scale gate captured 600/600 activation rows across 120 prompts and depths `[4, 8, 16, 32, 64]`; cross-depth stability 0.9257 with bootstrap CI [0.9067, 0.9273]; benign-control FPR 0.0000. |

## Bottom Line

The new D1 branch has four positive or continue-worthy gates: PX-050, PX-051, PX-052, and PX-054. PX-050 is the strongest publishable D1 lane, with a final manuscript draft, bounded paper package, and parser-stress appendix. PX-054 is now a bounded mechanistic-characterization positive, not a deployed safety-defense result. PX-053 remains a failed simulation/design result that needs redesign before any human-factors claim. PX-049 should be parked as a negative live-agent result unless the agent harness is redesigned to produce real install actions.
