# EXP02 Safety Schema Gate Result

Generated: 2026-06-18T19:12:02.571634+00:00

Status: **PASS**

## What This Gate Proves

This is a positive readiness gate, not a model-safety claim. It proves that EXP02 can proceed with public-source metadata, redacted manifests, strict holdout roles, a trace-label schema, and intervention actions without committing harmful prompt text or running model generations.

## Gate Checks

| Check | Result |
|---|---:|
| `accessible_sources` | `True` |
| `redacted_rows` | `True` |
| `unsafe_and_benign_labels` | `True` |
| `strict_holdout_present` | `True` |
| `benign_control_present` | `True` |
| `no_raw_text_in_manifest` | `True` |
| `synthetic_trace_count` | `True` |
| `trace_label_coverage` | `True` |
| `no_model_calls` | `True` |

## Source Summary

| Source | Status | Rows visible | Sampled rows | Role | Columns |
|---|---|---:|---:|---|---|
| `strongreject_validation` | `FAILED` | 0 | 0 | `schema_calibration` | `` |
| `wildjailbreak_train` | `ACCESSIBLE` | 2210 | 40 | `detector_dev` | `label, prompt` |
| `jbb_behaviors_harmful` | `ACCESSIBLE` | 100 | 30 | `strict_behavior_holdout_test` | `Behavior, Category, Goal, Index, Source, Target` |
| `jbb_behaviors_benign` | `ACCESSIBLE` | 100 | 30 | `benign_control_test` | `Behavior, Category, Goal, Index, Source, Target` |

## Label And Split Counts

- Safety labels: `{'benign_control': 35, 'unsafe_request': 65}`
- Split roles: `{'benign_control_test': 30, 'detector_dev': 40, 'strict_behavior_holdout_test': 30}`
- Synthetic trace rows: `12`
- Trace label coverage: `['benign_reasoning', 'false_positive_challenge', 'override_attempt', 'refusal_boundary', 'risk_recognition', 'safe_redirect']`

## Claim Boundary

This gate does not prove detector F1, intervention effectiveness, or attack-success reduction. It only authorizes a safe next phase: generate or collect step traces under this schema, keep unsafe content out of committed artifacts, and evaluate a detector/intervention on held-out categories and benign controls.
