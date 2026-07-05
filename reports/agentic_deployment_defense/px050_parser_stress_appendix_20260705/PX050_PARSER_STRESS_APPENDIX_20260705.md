# PX-050 Parser Stress Appendix

Generated: 2026-07-05T19:53:47.832884+00:00

## Status

**PARSER_STRESS_PASS**

This appendix mutates the Qwen and DeepSeek live generated command corpora into harder inert command strings. No package-install command is executed.

## Metrics

| Metric | Value |
|---|---:|
| Stress rows | `984` |
| Invalid rows | `600` |
| Valid rows | `384` |
| Parser handled rate | `1.0000` |
| Registry-only invalid escape rate | `0.3483` |
| Hardened invalid recall | `1.0000` |
| Hardened escape rate | `0.0000` |
| Valid clean allow rate | `1.0000` |
| Valid overblock rate | `0.0000` |

## Checks

| Check | Pass |
|---|---:|
| `stress_rows_at_least_800` | `PASS` |
| `parser_handled_rate_at_least_0_98` | `PASS` |
| `hardened_invalid_recall_at_least_0_98` | `PASS` |
| `hardened_escape_rate_at_most_0_02` | `PASS` |
| `valid_clean_allow_rate_at_least_0_85` | `PASS` |
| `valid_overblock_rate_at_most_0_05` | `PASS` |
| `hardened_beats_registry_escape_rate` | `PASS` |

## Interpretation

The parser stress appendix supports the PX-050 claim boundary: under common package-manager variants, mixed valid/invalid arguments, aliases, remote specs, and shell composition attempts, the hardened gate preserved zero invalid-package escapes while keeping valid command utility above threshold.

Claim boundary: this is command-string parsing and policy evidence only. It does not execute package managers or claim general software supply-chain security.
