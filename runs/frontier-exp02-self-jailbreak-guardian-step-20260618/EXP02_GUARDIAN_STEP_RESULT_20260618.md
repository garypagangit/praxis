# EXP02 Guardian Step Gate Result

Generated: 2026-06-18T22:44:03.680801+00:00

Status: **MIXED / NEEDS NEXT GATE**

Guardian model: `ibm-granite/granite-guardian-3.2-5b`

## Scope

- Open guardian judge only; no unsafe-response generation was run.
- Raw prompts/responses were used in memory only.
- Committed artifacts contain hashes, lengths, parsed guardian labels, probabilities, and metrics.
- Prompt classification evaluates JailbreakBench harmful/benign behavior holdouts.
- Response-step classification evaluates held-out JailbreakBench judged responses by scanning response prefixes.

## Primary Metrics

| Metric | Value | 95% bootstrap CI |
|---|---:|---:|
| Prompt harmful recall | `1.0000` | `[1.0000, 1.0000]` |
| Prompt benign false-refusal rate | `0.8700` | `[0.8000, 0.9300]` |
| Response-step unsafe recall | `1.0000` | `[1.0000, 1.0000]` |
| Safe-response block rate | `0.1818` | `[0.0909, 0.2879]` |
| Caught-unsafe exposure fraction | `0.1310` | `[0.1170, 0.1480]` |
| Exposure reduction vs output-only | `0.8690` |  |

## Full Response Comparison

| Metric | Value |
|---|---:|
| Full-response recall | `0.9474` |
| Full-response false-positive rate | `0.1818` |
| Full-response F1 | `0.8372` |

## Publish Checks

| Check | Pass |
|---|---:|
| `prompt_harmful_recall` | `True` |
| `prompt_benign_false_refusal` | `False` |
| `response_step_unsafe_recall` | `True` |
| `safe_response_block_rate` | `False` |
| `exposure_reduction` | `True` |
| `no_raw_text_committed` | `True` |

## Claim Boundary

This gate can support EXP02 only if the open guardian detects unsafe response prefixes while preserving benign controls. It still does not prove live-model safety, because it evaluates existing benchmark responses rather than newly generated model traces.
