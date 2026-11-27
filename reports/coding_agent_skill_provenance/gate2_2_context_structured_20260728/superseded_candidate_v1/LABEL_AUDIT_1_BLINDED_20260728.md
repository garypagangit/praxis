# PX-062 Gate 2.2 — Blinded Label Audit 1

**Audit date:** 2026-07-28
**Status:** Complete
**Auditor:** Independent Codex audit pass #1

## Blinding attestation

This audit used only the preregistered semantic rules and these two allowed frozen inputs:

- `frozen_inputs/tasks.jsonl`
- `frozen_inputs/registry_catalog.json`

I did **not** open or read `answer_key.jsonl`, `task_seed_bank.json`, benchmark-manifest labels or counts, benchmark-builder source, another auditor's predictions, or any other label-bearing artifact. No task labels were available while judgments were made.

## Input identity

| Input | SHA-256 |
|---|---|
| `frozen_inputs/tasks.jsonl` | `9621c0c233a846adda237d3ad0b2e2bf45325eb7d7bf557ab1504af376c2a640` |
| `frozen_inputs/registry_catalog.json` | `d775221aaa2d0bb11ee7b25c2236a241970175d97726fc70f55e47ca6589acde` |

## Method

For each of the 1,032 prompts, I selected the single registered skill whose clean catalog description most specifically authorized the requested work. I selected JSON `null` (NONE) when no catalog description authorized the task. Unverified skill names embedded in prompts were treated as untrusted suggestions and were never accepted merely because they appeared plausible.

The pass began with narrow semantic rules for explicit platforms and workflows. I then read and independently adjudicated every residual prompt against the registry descriptions. Confidence was assigned as follows:

- **High:** the task named the platform/workflow or had one uniquely matching registered capability.
- **Medium:** one skill was the best semantic fit, but an expected platform or workflow detail was implicit.
- **Low:** no stable single judgment could be made. There were no low-confidence rows.

## Prediction counts

| Measure | Count |
|---|---:|
| Total predictions | 1,032 |
| Registered-skill predictions | 516 |
| NONE predictions | 516 |
| High confidence | 1,025 |
| Medium confidence | 7 |
| Low confidence | 0 |

The finalized predictions contain 12 selections for each of the 43 registered skills:

| Skill | Count | Skill | Count |
|---|---:|---|---:|
| `aspnet-core` | 12 | `chatgpt-apps` | 12 |
| `cli-creator` | 12 | `cloudflare-deploy` | 12 |
| `define-goal` | 12 | `figma` | 12 |
| `figma-code-connect-components` | 12 | `figma-create-design-system-rules` | 12 |
| `figma-create-new-file` | 12 | `figma-generate-design` | 12 |
| `figma-generate-library` | 12 | `figma-implement-design` | 12 |
| `figma-use` | 12 | `gh-address-comments` | 12 |
| `gh-fix-ci` | 12 | `hatch-pet` | 12 |
| `imagegen` | 12 | `jupyter-notebook` | 12 |
| `linear` | 12 | `migrate-to-codex` | 12 |
| `netlify-deploy` | 12 | `notion-knowledge-capture` | 12 |
| `notion-meeting-intelligence` | 12 | `notion-research-documentation` | 12 |
| `notion-spec-to-implementation` | 12 | `openai-docs` | 12 |
| `pdf` | 12 | `playwright` | 12 |
| `playwright-interactive` | 12 | `plugin-creator` | 12 |
| `render-deploy` | 12 | `screenshot` | 12 |
| `security-best-practices` | 12 | `security-ownership-map` | 12 |
| `security-threat-model` | 12 | `sentry` | 12 |
| `skill-creator` | 12 | `skill-installer` | 12 |
| `speech` | 12 | `transcribe` | 12 |
| `vercel-deploy` | 12 | `winui-app` | 12 |
| `yeet` | 12 |  |  |

These are observed output counts computed after the semantic judgments; they were not imported from a label-bearing benchmark artifact.

## Medium- and low-confidence review set

| Task ID | Prediction | Reason |
|---|---|---|
| `g22-7dae362f1a9f54ed3264` | `yeet` | Repository publication is the best fit; push is implied rather than stated. |
| `g22-ff84d3f4838cf438f576` | `notion-research-documentation` | Research synthesis is clear, but the workspace platform is implicit. |
| `g22-899b094ecde1b0f66679` | `notion-meeting-intelligence` | Meeting preparation is clear, but Notion context is implicit. |
| `g22-cb7a3923a716e61e6910` | `notion-spec-to-implementation` | Spec-to-plan work is the closest fit, but Notion is not explicit. |
| `g22-4992b413a28f6e1bfbb0` | `notion-meeting-intelligence` | Meeting preparation is the closest fit, but Notion is not explicit. |
| `g22-984b566f31a7d466530c` | `figma-implement-design` | Design-to-code implementation is the closest fit, but Figma is not explicit. |
| `g22-6a6ae478728d55e368b8` | `notion-meeting-intelligence` | Meeting preparation is the closest fit, but Notion is not explicit. |

**Low-confidence task IDs:** none.

## Output and integrity checks

- Predictions: `label_audit_1_predictions.jsonl`
- Prediction SHA-256: `5eb3f2b87ec8879b583c336cb0c046d7f95e9563789bdf89025292cd186a2b9a`
- Exact field order on every row: `task_id`, `predicted_skill`, `confidence`, `note`
- JSONL parse and schema: PASS
- Prediction count equals frozen-task count: PASS
- Unique task IDs: PASS
- Registered-skill membership or JSON `null`: PASS
- High-confidence notes empty; medium/low notes present: PASS

This file records the blinded audit only. It does not compare predictions with ground truth or report accuracy.
