# PX-011 HalluHard Repair Gate

Generated: 2026-06-30T11:23:18+00:00

Status: **REPAIR GATE MIXED**

## Claim Boundary

This is a local repair analysis over frozen source-conditioned HalluHard model outputs. It does not generate new model responses and does not broaden the claim beyond the research_questions lane.

## Headline Result

The original strict parser marked only `25`/`250` supported generations parse-valid (`0.1000`). A repair parser recovered `192`/`250` supported generations (`0.7680`). After recomputing the same DOI/arXiv/title/year/content verifier against matched supported and shifted-source negative pairs, verifier macro F1 is `0.5652` versus field-presence macro F1 `0.4613`.

This means PX-011 is not a broad HalluHard positive, but the live-model failure was largely an output-format/parser problem rather than a total absence of source-grounded citation content.

## Metrics

| Metric | Original strict gate | Repair gate |
|---|---:|---:|
| Supported generations recovered | `25` | `192` |
| Supported recovery rate | `0.1000` | `0.7680` |
| Supported claims passing verifier | `25` | `63` |
| Supported rate | `0.1000` | `0.2520` |
| Verifier macro F1 | `0.4357` | `0.5652` |
| Always-supported macro F1 | `0.3333` | `0.3333` |
| Field-presence macro F1 | `0.4048` | `0.4613` |

## Repair Status Counts

| Repair status | Rows |
|---|---:|
| `regex_repair` | `334` |
| `strict_json` | `50` |
| `unrepairable:Invalid control character at: line 1 column 136 (char 135)` | `2` |
| `unrepairable:Invalid control character at: line 1 column 142 (char 141)` | `2` |
| `unrepairable:Invalid control character at: line 1 column 147 (char 146)` | `2` |
| `unrepairable:Invalid control character at: line 1 column 152 (char 151)` | `2` |
| `unrepairable:Invalid control character at: line 1 column 92 (char 91)` | `2` |
| `unrepairable:no_json_object` | `106` |

## Decision

- Promote PX-011 only as a bounded repair/parser gate over frozen model outputs.
- The next live run should use constrained JSON/schema decoding or a shorter field-by-field prompt before claiming HalluHard utility.
- Do not claim a general HalluHard benchmark solution; this result is research-lane only and depends on deterministic source metadata.

## Artifacts

- Raw analysis JSON: [`runs/halluhard-repair-gate-20260630/halluhard_repair_gate.json`](../../runs/halluhard-repair-gate-20260630/halluhard_repair_gate.json)
- Repaired rows CSV: [`runs/halluhard-repair-gate-20260630/halluhard_repair_rows.csv`](../../runs/halluhard-repair-gate-20260630/halluhard_repair_rows.csv)
- Original source-conditioned gate: [`HALLUHARD_SOURCE_CONDITIONED_RESPONSE_GATE_20260628.md`](HALLUHARD_SOURCE_CONDITIONED_RESPONSE_GATE_20260628.md)
