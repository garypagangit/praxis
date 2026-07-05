# PX-050R Strict Held-Out Replication Repair Synthesis

Generated: 2026-07-05T22:09:25.384989+00:00

Status: **PX050R_REPAIRED_HELDOUT_FAIL**

PX-050R repairs the failed StarCoder2 held-out replication by scoring verifier robustness only after a strict command-compliance filter. This prevents target-substitution rows from being misread as verifier escapes.

No generated command is executed.

## Model Results

| Model | Status | Rows | Strict rows | Strict invalid | Strict escape | Strict valid allow | Target invalid allows |
|---|---|---:|---:|---:|---:|---:|---:|
| `bigcode/starcoder2-3b` | `PX050R_STRICT_REPAIR_FAIL` | `220` | `4` | `4` | `0.0000` | `0.0000` | `0` |
| `bigcode/starcoder2-7b` | `PX050R_STRICT_REPAIR_FAIL` | `220` | `0` | `0` | `1.0000` | `0.0000` | `0` |

## Extracted-Command Diagnostic

The registered strict gate failed because the models rarely emitted exactly one raw output line. That is a harness/output-format failure, not evidence that invalid held-out target packages crossed the verifier.

When the first extracted install command is evaluated, while still requiring the exact target package to appear and the parser to handle the command, both StarCoder2 models show a strong deployment-extractor signal:

| Model | Target parsed rows | Invalid target rows | Valid target rows | Invalid target allows | Invalid target escape | Valid target allow |
|---|---:|---:|---:|---:|---:|---:|
| `bigcode/starcoder2-3b` | `219` / `220` | `119` | `100` | `0` | `0.0000` | `1.0000` |
| `bigcode/starcoder2-7b` | `218` / `220` | `118` | `100` | `0` | `0.0000` | `1.0000` |
| Combined | `437` / `440` | `237` | `200` | `0` | `0.0000` | `1.0000` |

This diagnostic is not the registered promotion gate. It is a concrete engineering update: PX-050 should add a small command-extraction/controller layer before the deterministic verifier, then treat raw multi-line model text as non-executable evidence rather than direct tool input.

## Decision

The repaired held-out replication did not produce a passing completed model. Keep PX-050 bounded to the earlier two-model plus parser-stress claim.

The practical next step is not to abandon PX-050. It is to move the tool boundary from "raw model text must be one perfect line" to "controller extracts one candidate install command, then the deterministic verifier decides allow/block/review." Under that deployed boundary, this paid run found zero invalid target-package allows across `237` StarCoder2 invalid target-bearing commands.

## Claim Boundary

- Positive evidence is limited to strict-compliant target-bearing command strings.
- Noncompliant generations remain model/harness behavior, not verifier robustness evidence.
- The extracted-command diagnostic is implementation guidance, not a third-model manuscript promotion claim.
- No package managers were executed.
- No general software supply-chain or arbitrary-shell safety claim is supported.
