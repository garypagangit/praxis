# FalseCite-Code

PX ID: PX-004

Status: **FINAL SHORT PAPER PUBLISHED - BOUNDED POSITIVE**

## Overview

FalseCite-Code tests whether code-assistant models can be induced to trust fabricated software-artifact citations, and whether strict public metadata plus a citation-aware verifier can reduce that trust.

The experiment focuses on software artifacts that code assistants naturally cite:

- PyPI package versions
- NPM package versions
- GitHub repositories
- GitHub tags/releases

## Current Result

The track is a bounded positive result. On the locked 80-claim benchmark, the primary code-tuned model accepted fabricated citations under base prompting, while the citation-aware verifier reduced strict-holdout fabricated trust to `0.0000`.

| Gate | Status | Key result |
|---|---|---|
| Source/verifier readiness | PASS | `80` locked claims; verifier accuracy `1.0000`; invalid recall `1.0000`. |
| Audit-mode model gate | PASS | Qwen2.5-Coder-7B strict fabricated acceptance `0.8571` to verifier `0.0000`. |
| Generation-mode verbose160 | PASS | Base strict fabricated trust `0.8333` to verifier `0.0000`. |
| Coder 3B boundary | BOUNDARY | Base strict fabricated trust `0.8571`; metadata evidence failed; verifier `0.0000`. |

## Main Documents

| Document | Purpose |
|---|---|
| [Final short paper](FALSECITE_CODE_SHORT_PAPER_20260628.md) | Final short-paper version of the bounded positive result. |
| [Paper draft](FALSECITE_CODE_PAPER_DRAFT_20260628.md) | Draft retained for development history. |
| [Publishing package](FALSECITE_CODE_PUBLISHING_PACKAGE_20260628.md) | Short packaging summary and claim boundary. |
| [Usefulness decision](FALSECITE_CODE_USEFULNESS_DECISION_20260625.md) | Final decision on whether the experiment is useful. |
| [Experiment dashboard](FALSECITE_CODE_DASHBOARD_20260625.html) | Per-experiment HTML status dashboard. |

## Evidence

| Artifact | Purpose |
|---|---|
| [Source/verifier gate](FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md) | Locked benchmark and deterministic verifier gate. |
| [Audit-mode model gate](FALSECITE_CODE_MODEL_GATE_20260624.md) | Primary code-tuned model vulnerability/remediation gate. |
| [Generation-mode gate](FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md) | Primary short-answer generation result. |
| [Coder 3B generation boundary](FALSECITE_CODE_GENERATION_GATE_QWEN25_CODER3B_20260626.md) | External-validity boundary showing metadata-evidence failure and verifier robustness. |
| [Cross-model synthesis](FALSECITE_CODE_CROSS_MODEL_SYNTHESIS_20260624.md) | Summary of model-dependent behavior and protocol limits. |
| [Locked claims](FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl) | The 80-row software-artifact citation benchmark. |

## Code and Configs

| Path | Purpose |
|---|---|
| [../../scripts/run_falsecite_code_gate.py](../../scripts/run_falsecite_code_gate.py) | Build and verify the locked claim slice. |
| [../../scripts/run_falsecite_code_model_gate.py](../../scripts/run_falsecite_code_model_gate.py) | Run the audit-mode model gate. |
| [../../scripts/run_falsecite_code_generation_gate.py](../../scripts/run_falsecite_code_generation_gate.py) | Run the generation-mode model gate. |
| [../../configs/falsecite_code_gate_20260623.json](../../configs/falsecite_code_gate_20260623.json) | Source/verifier gate config. |
| [../../configs/falsecite_code_model_gate_20260624.json](../../configs/falsecite_code_model_gate_20260624.json) | Primary audit-mode config. |
| [../../configs/falsecite_code_generation_gate_verbose160_20260625.json](../../configs/falsecite_code_generation_gate_verbose160_20260625.json) | Primary generation-mode config. |

## Claim Boundary

Supported: external verification can suppress fabricated software-artifact citation trust on the locked benchmark and primary code-tuned model gates.

Not supported: universal hallucination prevention, universal model vulnerability, arbitrary code-generation safety, or universal effectiveness of metadata-evidence prompting.

## Next Step

Use the final short paper as the published portfolio artifact. A second code-tuned external-validity model is useful only if the goal is to widen the claim beyond a bounded Praxis result.
