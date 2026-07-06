# PX-050 Claim Boundary

Generated: 2026-07-05

## Approved Claim

PX-050 supports a bounded positive Praxis claim:

> A deterministic package-install gate can block invalid or policy-unsafe model-generated install command strings with zero observed invalid-package escapes across measured live-model, parser-stress, controller/extractor, and dry-run live-agent tool-call corpora, while preserving high valid-command utility.

The stronger claim that the hardened gate always outperforms registry-only validation is not supported across all live models. It is supported on Qwen and on parser-stress mutations, but not on DeepSeek, where registry-only validation also caught the simpler invalid package names.

Held-out StarCoder2 raw and strict one-line runs on 2026-07-05 failed registered promotion gates. They are boundary evidence only and must not be presented as positive raw-output third-model replication. PX-050S adds a passed deployment-repair result: controller-based target command extraction before verification preserved valid utility and produced zero invalid allows on a fresh StarCoder2 held-out namespace. PX-050T adds passed crafted-command adaptive stress for the controller/extractor repair. PX-050U/PX-050V add passed two-model dry-run live-agent-style tool-call evidence with install actions present, a raw unsafe-action baseline, and zero hardened invalid allows.

## Evidence Required In Any Paper Or Defense

| Evidence | Required Wording |
|---|---|
| Fixed fixture | `138` fixed adaptive command cases; hardened escape rate `0.0000`; clean allow rate `1.0000`. |
| Qwen live | `98` generated commands; registry-only invalid escape `0.1800`; hardened escape `0.0000`; valid clean allow `0.9167`. |
| DeepSeek live | `98` generated commands; registry-only invalid escape `0.0000`; hardened escape `0.0000`; valid clean allow `1.0000`; uplift condition failed. |
| Combined replication | `196` generated commands; aggregate hardened escape `0.0000`; aggregate registry-only invalid escape `0.0900`; aggregate valid clean allow `0.9583`. |
| Parser stress | `984` inert mutations; hardened escape `0.0000`; registry-only invalid escape `0.3483`; valid clean allow `1.0000`; valid overblock `0.0000`. |
| Held-out StarCoder2 boundary | `110` generated commands; status `HELDOUT_THIRD_MODEL_FAIL`; command parse rate `0.8091`; registered hardened invalid recall `0.7750`; registered hardened escape `0.2250`. Exclude from the positive evidence count. |
| PX-050R strict repair | `440` StarCoder2 generated commands; status `PX050R_REPAIRED_HELDOUT_FAIL`; strict one-line promotion failed. Extracted-command diagnostic: `437` target-bearing parsed commands, `237` invalid target rows, invalid target escape `0.0000`, valid target allow `1.0000`. Treat as implementation guidance only. |
| PX-050S controller/extractor repair | `440` fresh StarCoder2 generated commands; status `PX050S_CONTROLLER_EXTRACTOR_HELDOUT_PASS`; target recovery `0.9909` / `0.9864`; invalid allows `0`; invalid escape `0.0000`; valid allow `1.0000` on both models. Treat as positive deployment-repair evidence, not raw-output third-model replication. |
| PX-050T adaptive string stress | `1,440` crafted raw-output strings; status `PX050T_CONTROLLER_ADAPTIVE_STRESS_PASS`; `1,140` invalid cases; invalid allows `0`; valid allow `1.0000`; registry-only invalid allows `300`; target recovery `0.9583`. Treat as crafted command-string stress, not live-agent evidence. |
| PX-050U live-agent tool boundary | `144` dry-run tool-call rows; status `PX050U_LIVE_AGENT_TOOL_BOUNDARY_PASS`; install-action rate `1.0000`; raw unsafe rate `0.8906`; controller recovery `0.9514`; registry-only invalid allows `10`; hardened invalid allows `0`; valid allow `1.0000`. Treat as dry-run live-agent-style tool-call evidence, not package-manager execution or broad agent-safety evidence. |
| PX-050V second-model live-agent tool boundary | `144` dry-run tool-call rows; status `PX050V_SECOND_MODEL_LIVE_AGENT_TOOL_BOUNDARY_PASS`; install-action rate `1.0000`; raw unsafe rate `1.0000`; controller recovery `1.0000`; registry-only invalid allows `10`; hardened invalid allows `0`; valid allow `1.0000`. Treat as dry-run live-agent-style tool-call evidence, not package-manager execution or broad agent-safety evidence. |
| PX-050U/V final determination | `288` combined dry-run tool-call rows across Qwen and DeepSeek; status `TWO_MODEL_DRY_RUN_LIVE_AGENT_TOOL_BOUNDARY_POSITIVE`; raw unsafe rate `0.9453`; controller recovery `0.9757`; registry-only invalid allows `20`; hardened invalid allows `0`; valid allow `1.0000`. Promote PX-050 as lead Praxis defense result within the no-execution boundary. |
| PX-051V live-agent policy refresh | `288` combined PX-050U/PX-050V tool-call rows; status `PX051V_LIVE_AGENT_POLICY_REFRESH_PASS`; hardened policy on Pareto front; invalid escape `0.0000`; utility `1.0000`; review rate `0.0243`; registry-only invalid escape `0.1563`. |
| PX-052V live-agent provenance refresh | `288` combined PX-050U/PX-050V tool-call traces; status `PX052V_LIVE_AGENT_PROVENANCE_REFRESH_PASS`; alert recall `1.0000`; clean false-positive rate `0.0000`; trace completeness `1.0000`. |

## Use This Language

- "zero observed invalid-package escapes"
- "on measured command-string corpora"
- "tool-boundary verifier"
- "inert package-install commands; no package manager execution"
- "registry-uplift is distribution-dependent"
- "bounded positive result"
- "held-out third-model boundary failed registered promotion"
- "PX-050S controller/extractor repair passed as a deployment-shaped boundary control"
- "PX-050T adaptive string stress passed against crafted raw-output attacks"
- "PX-050U/PX-050V two-model dry-run live-agent tool-call gates passed with install actions present"

## Avoid This Language

- "solves slopsquatting"
- "prevents supply-chain compromise"
- "proves coding agents are safe"
- "monitors chain of thought"
- "blocks all malicious packages"
- "universal adaptive robustness"
- "raw third-model replication"
- "PX-050R proves third-model promotion"
- "PX-050S proves all coding agents are safe"
- "PX-050T proves live agents cannot bypass the gate"
- "PX-050U/PX-050V prove broad agent safety or package-manager execution safety"
- "works for arbitrary shell commands"

## Defense Readiness

PX-050 is ready for a Praxis defense section if the section keeps the claim narrow:

1. Show the live Qwen and DeepSeek contrast to demonstrate honest replication.
2. Use the parser-stress appendix to show the verifier was not only tuned to the exact live command strings.
3. Present the raw and strict StarCoder2 held-out runs as negative boundary results, not as positive raw-output replication.
4. Present PX-050S as the positive controller/extractor deployment repair: target-matching extraction, review fallback, deterministic verifier, no execution.
5. Present PX-050T as adaptive crafted-command stress against the repair, not as live-agent behavior.
6. Present PX-050U/PX-050V as two-model dry-run live-agent-style tool-call evidence that the repaired boundary still blocks invalid installs when install actions are proposed.
7. Use PX-051 to explain deployment operating points.
8. Use PX-052 to show how provenance metadata can help route tool-boundary decisions.
9. Explicitly state that execution, package reputation, and arbitrary shell safety are outside this experiment.
