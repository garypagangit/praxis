# PX-050 Claim Boundary

Generated: 2026-07-05

## Approved Claim

PX-050 supports a bounded positive Praxis claim:

> A deterministic package-install gate can block invalid or policy-unsafe model-generated install command strings with zero observed invalid-package escapes across two open-weight coding models, while preserving high valid-command utility.

The stronger claim that the hardened gate always outperforms registry-only validation is not supported across all live models. It is supported on Qwen and on parser-stress mutations, but not on DeepSeek, where registry-only validation also caught the simpler invalid package names.

Held-out StarCoder2 third-model runs on 2026-07-05 failed registered promotion gates. They are boundary evidence only and must not be presented as positive third-model replication. PX-050R adds an implementation lesson: controller-based command extraction before verification is promising, but it is not a registered manuscript promotion.

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
| Policy refresh | Hardened policy on Pareto front; invalid escape `0.0000`; utility `0.9583`; review rate `0.0000`. |
| Provenance refresh | Alert recall `1.0000`; clean false-positive rate `0.0000`; trace completeness `1.0000`. |

## Use This Language

- "zero observed invalid-package escapes"
- "on measured command-string corpora"
- "tool-boundary verifier"
- "inert package-install commands; no package manager execution"
- "registry-uplift is distribution-dependent"
- "bounded positive result"
- "held-out third-model boundary failed registered promotion"
- "command-extractor diagnostic suggests an implementation update"

## Avoid This Language

- "solves slopsquatting"
- "prevents supply-chain compromise"
- "proves coding agents are safe"
- "monitors chain of thought"
- "blocks all malicious packages"
- "universal adaptive robustness"
- "third-model replication"
- "PX-050R proves third-model promotion"
- "works for arbitrary shell commands"

## Defense Readiness

PX-050 is ready for a Praxis defense section if the section keeps the claim narrow:

1. Show the live Qwen and DeepSeek contrast to demonstrate honest replication.
2. Use the parser-stress appendix to show the verifier was not only tuned to the exact live command strings.
3. Present the StarCoder2 held-out runs as negative boundary results, not as positive replication.
4. Present PX-050R's extracted-command diagnostic as implementation guidance for a controller/extractor layer.
5. Use PX-051 to explain deployment operating points.
6. Use PX-052 to show how provenance metadata can help route tool-boundary decisions.
7. Explicitly state that execution, package reputation, and arbitrary shell safety are outside this experiment.
