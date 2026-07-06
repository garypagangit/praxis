# D1 New Experiment Follow-On Rollup

Generated: 2026-07-05T18:28:46.751701+00:00

## Decision Table

| ID | Experiment | Status | Decision | Key result |
|---|---|---|---|---|
| `PX-049` | Agentic slopsquatting live gate | `LIVE_GATE_FAIL` | Park or redesign | Live Qwen2.5-Coder run produced zero install actions, so no unsafe-install gap existed to close. |
| `PX-050` | Adaptive deterministic agent defenses | `TWO_MODEL_DRY_RUN_LIVE_AGENT_TOOL_BOUNDARY_POSITIVE` | Lead D1 paper candidate | Qwen and DeepSeek live corpus plus parser stress: aggregate hardened escape 0.0000 on 196 live commands; parser-stress hardened escape 0.0000 on 984 inert mutations; valid clean allow 0.9583 live and 1.0000 stress. Raw and strict one-line StarCoder2 promotion gates failed, but PX-050S passed a fresh controller/extractor repair over 440 StarCoder2 commands. PX-050T then passed a 1,440-row adaptive string stress suite with 0 invalid allows and registry-only invalid allows 300. PX-050U/PX-050V passed two dry-run live-agent tool-call gates over 288 combined tasks with install-action rate 1.0000, raw unsafe rate 0.9453, hardened invalid allows 0, and valid allow 1.0000. |
| `PX-051` | Security-utility Pareto gate | `LIVE_POLICY_REFRESH_PASS` | Continue / positive gate | Combined live corpus: hardened policy on Pareto front, invalid escape 0.0000, utility 0.9583. |
| `PX-052` | Provenance-aware tool-boundary retrofit | `LIVE_PROVENANCE_REFRESH_PASS` | Continue / positive gate | Combined live corpus: alert recall 1.0000; clean FPR 0.0000; trace completeness 1.0000. |
| `PX-053` | Approval fatigue vs. security simulation | `SIMULATION_GATE_FAIL` | Do not promote | Risk-scored compromise 0.0636. |
| `PX-054` | Refusal geometry across recurrent depth | `SCALE_GATE_PASS` | Bounded characterization positive | Safe Huginn scale gate captured 600/600 activation rows across 120 prompts and depths `[4, 8, 16, 32, 64]`; cross-depth stability 0.9257 with bootstrap CI [0.9067, 0.9273]; benign-control FPR 0.0000. |

## Bottom Line

The new D1 branch has four positive or continue-worthy gates: PX-050, PX-051, PX-052, and PX-054. PX-050 remains the strongest publishable D1 lane and is now the lead Praxis defense result. The raw held-out StarCoder2 gates are still boundary failures, but PX-050S converts the PX-050R diagnostic into a passed deployment repair: a controller/extractor selects a target-matching install command before the deterministic verifier, with review as the safe fallback. PX-050T strengthens that repair with adaptive crafted raw-output stress, showing zero invalid allows where registry-only checking would have allowed 300 invalid cases. PX-050U and PX-050V add the missing two-model dry-run live-agent tool-boundary evidence: Qwen and DeepSeek produced install actions on every row, established a raw unsafe-action baseline, and still yielded zero hardened invalid allows. PX-054 is a bounded mechanistic-characterization positive, not a deployed safety-defense result. PX-053 remains a failed simulation/design result that needs redesign before any human-factors claim. PX-049 should remain parked as the earlier negative harness result because it produced no install actions.
