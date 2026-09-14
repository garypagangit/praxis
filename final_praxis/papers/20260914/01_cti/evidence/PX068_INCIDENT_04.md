# PX-068 technical incident 04 — inherited validity-summary defect

## Finding

The post-terminal completeness audit found that the frozen inference runner and frozen analyzer use different definitions of parser validity.

- The PX-068 runner applies the frozen exact parser `(?:Answer: )?([A-E])` and records A, B, C, D, or E as valid.
- The PX-068 analyzer correctly uses those parsed labels for accuracy, but imports `valid_answer()` from the earlier PX-003 four-option analyzer for its invalid-rate summaries.
- That inherited helper treats E as valid only on rows whose expected answer is E. A parser-valid but incorrect E response on an A–D truth row is therefore mislabeled invalid in the analyzer's invalid-rate field.

This defect changes invalid counts and the numeric invalid-rate safety inputs. It does not change any correctness value, paired accuracy difference, confidence interval, McNemar test, Holm correction, router metric, or Gates 1, 2, 3, and 5.

## Independent A–E validity audit

Complete-corpus parser-valid counts were recomputed mechanically from the already-frozen `parsed_answer` field, accepting exactly A–E and performing no reparse or alternate answer extraction.

| Model | Policy | Frozen analyzer valid | Correct A–E parser valid | Rows |
|---|---|---:|---:|---:|
| Llama | vanilla | 525 | 630 | 2,997 |
| Llama | relationship evidence | 1,452 | 1,571 | 2,997 |
| Llama | routed | 1,285 | 1,382 | 2,997 |
| Llama | oracle diagnostic | 886 | 968 | 2,997 |
| Qwen | vanilla | 67 | 67 | 2,997 |
| Qwen | relationship evidence | 2,029 | 2,116 | 2,997 |
| Qwen | routed | 1,279 | 1,332 | 2,997 |
| Qwen | oracle diagnostic | 712 | 725 | 2,997 |

Every corrected routed-minus-vanilla invalid-rate difference remains below the registered +0.01 ceiling in every primary scope:

| Scope | Llama corrected difference | Qwen corrected difference |
|---|---:|---:|
| all primary | −0.2509 | −0.4221 |
| eligible | −0.3196 | −0.5932 |
| ineligible | −0.2166 | −0.3367 |
| non-ATT&CK | −0.0231 | −0.0503 |
| other ATT&CK page types | −0.3933 | −0.5981 |

Gate 4 therefore passes under both the frozen analyzer values and the intended A–E parser-validity definition. The portfolio remains `FAIL_ROUTER_CONFIRMATION` because Gates 1 and 5 fail independently.

## Preservation

The raw `analysis.json` is not modified. No model output is reparsed to recover a label, no condition is re-estimated, and no gate is reclassified. The final report distinguishes the frozen analyzer's invalid-rate fields from the mechanically audited A–E parser-validity counts.
