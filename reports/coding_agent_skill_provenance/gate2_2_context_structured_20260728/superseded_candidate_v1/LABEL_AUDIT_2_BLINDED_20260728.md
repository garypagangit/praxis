# PX-062 Gate 2.2 Blinded Label Audit 2

**Date:** 2026-07-28
**Audit:** Independent blinded semantic label audit 2
**Rows judged:** 1,032 of 1,032

## Decision rule and method

For each task, I read the original user request and independently selected the
single registered skill whose description best matched the request's **primary
workflow**. I selected `NONE` only when no registered skill directly applied.
Unverified skill names embedded in prompts were treated as non-authoritative and
were checked only against the clean registry catalog.

I reviewed every prompt. An independently authored helper applied the resulting
semantic decision rules consistently across repeated phrasings. Close workflow
boundaries were reviewed explicitly, including the eight Figma workflows, four
Notion workflows, GitHub review/CI/publication workflows, browser automation
versus persistent interactive browsing, image generation versus screenshots,
skill creation versus installation, and the deployment-provider skills.

## Artifacts and SHA-256 hashes

| Artifact | SHA-256 |
|---|---|
| `frozen_inputs/tasks.jsonl` | `9621c0c233a846adda237d3ad0b2e2bf45325eb7d7bf557ab1504af376c2a640` |
| `frozen_inputs/registry_catalog.json` | `d775221aaa2d0bb11ee7b25c2236a241970175d97726fc70f55e47ca6589acde` |
| `PX062_GATE2_2_CONTEXT_STRUCTURED_PREREG_20260728.md` | `71cd79b107258cb96a76f2239e47496fa500e10922bae6a332f372892033d82b` |
| `label_audit_2_helper.py` | `e8aa4c6ea7143e6fdf0d2ddcef7c0260722dea2172e926a6e7e0fded57cbad15` |
| `label_audit_2_predictions.jsonl` | `7acd6e31b0adc5c4b5d2aeb15f3d8f545caded9601274cb40eedfcc466761513` |

## Counts

- Input task rows: 1,032
- Unique input task IDs: 1,032
- Prediction rows: 1,032
- Unique prediction task IDs: 1,032
- Registered-skill predictions: 516
- `NONE` predictions: 516
- High confidence: 1,032
- Medium confidence: 0
- Low confidence: 0

Each of the 43 registered skills was selected 12 times. These are observed
audit-output counts, not labels imported from another artifact.

## Medium- and low-confidence IDs

- Medium: none
- Low: none

## Integrity checks

- Every prediction has exactly the keys `task_id`, `predicted_skill`,
  `confidence`, and `note`.
- Every input task ID appears exactly once and in input order.
- No extra or missing task IDs were found.
- Every non-`NONE` prediction is an exact registered catalog name.
- Every confidence value is one of `high`, `medium`, or `low`.
- All high-confidence notes are empty; no medium/low note is required because
  there are no medium/low rows.
- JSON parsing succeeded for every input and prediction line.

## Blinding attestation

I did not open, read, query, compare against, infer labels from, or otherwise
access `answer_key.jsonl`, `task_seed_bank.json`, `benchmark_manifest.json`, any
builder source, tests, configuration counts, or any other label-bearing file.
The only source artifacts used to make semantic judgments were the frozen
`tasks.jsonl`, its adjacent `registry_catalog.json`, and the preregistered rule
that the best primary workflow skill should be chosen and `NONE` used only when
no registered skill directly applies. I did not compare these predictions with
an answer key. No benchmark or configuration artifact was modified.
