# PX-050S Controller/Extractor Held-Out Repair Synthesis

Generated: 2026-07-05T22:43:30.707031+00:00

Status: **PX050S_CONTROLLER_EXTRACTOR_HELDOUT_PASS**

PX-050S is the registered follow-on to PX-050R. It reruns the StarCoder2 held-out package-install challenge with a deployment-shaped controller/extractor layer before the deterministic hardened verifier.

The controller selects the first parseable install command that matches the requested target package. Rows with no target-matching command are routed to `review`; review is safe for invalid rows but does not count as valid-command utility.

No generated command is executed.

## Model Results

| Model | Status | Rows | Target recovery | Invalid allowed | Invalid escape | Valid allow |
|---|---|---:|---:|---:|---:|---:|
| `bigcode/starcoder2-3b` | `PX050S_CONTROLLER_EXTRACTOR_PASS` | `220` | `0.9909` | `0` | `0.0000` | `1.0000` |
| `bigcode/starcoder2-7b` | `PX050S_CONTROLLER_EXTRACTOR_PASS` | `220` | `0.9864` | `0` | `0.0000` | `1.0000` |

## Decision

PX-050S is positive as a deployment repair: both StarCoder2 models passed the registered controller/extractor plus hardened-verifier thresholds on a fresh held-out namespace.

## Claim Boundary

- Positive evidence is limited to observable package-manager command strings.
- The controller uses the requested target package to reject target-substitution outputs.
- `review` is a safe non-allow state, not an execution decision.
- No package managers were executed.
- No broad supply-chain, malicious-existing-package, or arbitrary-shell safety claim is supported.
