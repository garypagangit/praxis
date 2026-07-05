# PX-050 Claim Boundary

Generated: 2026-07-05

## Approved Claim

PX-050 supports a bounded positive Praxis claim:

> A deterministic package-install gate can block invalid or policy-unsafe model-generated install command strings with zero observed invalid-package escapes across two open-weight coding models, while preserving high valid-command utility.

The stronger claim that the hardened gate always outperforms registry-only validation is not supported across all live models. It is supported on Qwen and on parser-stress mutations, but not on DeepSeek, where registry-only validation also caught the simpler invalid package names.

## Evidence Required In Any Paper Or Defense

| Evidence | Required Wording |
|---|---|
| Fixed fixture | `138` fixed adaptive command cases; hardened escape rate `0.0000`; clean allow rate `1.0000`. |
| Qwen live | `98` generated commands; registry-only invalid escape `0.1800`; hardened escape `0.0000`; valid clean allow `0.9167`. |
| DeepSeek live | `98` generated commands; registry-only invalid escape `0.0000`; hardened escape `0.0000`; valid clean allow `1.0000`; uplift condition failed. |
| Combined replication | `196` generated commands; aggregate hardened escape `0.0000`; aggregate registry-only invalid escape `0.0900`; aggregate valid clean allow `0.9583`. |
| Parser stress | `984` inert mutations; hardened escape `0.0000`; registry-only invalid escape `0.3483`; valid clean allow `1.0000`; valid overblock `0.0000`. |
| Policy refresh | Hardened policy on Pareto front; invalid escape `0.0000`; utility `0.9583`; review rate `0.0000`. |
| Provenance refresh | Alert recall `1.0000`; clean false-positive rate `0.0000`; trace completeness `1.0000`. |

## Use This Language

- "zero observed invalid-package escapes"
- "on measured command-string corpora"
- "tool-boundary verifier"
- "inert package-install commands; no package manager execution"
- "registry-uplift is distribution-dependent"
- "bounded positive result"

## Avoid This Language

- "solves slopsquatting"
- "prevents supply-chain compromise"
- "proves coding agents are safe"
- "monitors chain of thought"
- "blocks all malicious packages"
- "universal adaptive robustness"
- "works for arbitrary shell commands"

## Defense Readiness

PX-050 is ready for a Praxis defense section if the section keeps the claim narrow:

1. Show the live Qwen and DeepSeek contrast to demonstrate honest replication.
2. Use the parser-stress appendix to show the verifier was not only tuned to the exact live command strings.
3. Use PX-051 to explain deployment operating points.
4. Use PX-052 to show how provenance metadata can help route tool-boundary decisions.
5. Explicitly state that execution, package reputation, and arbitrary shell safety are outside this experiment.
