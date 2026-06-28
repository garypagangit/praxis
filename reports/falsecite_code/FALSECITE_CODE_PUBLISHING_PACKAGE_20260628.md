# FalseCite-Code Publishing Package

Date: 2026-06-28

PX ID: PX-004

Status: **WORKING POSITIVE - PACKAGING READY**

## Title

FalseCite-Code: Software-Artifact Citation Poisoning in Code-Assistant Prompts

## Objective

Test whether code-assistant models can be induced to trust fabricated software-artifact citations, and whether strict external package/repository metadata plus a citation-aware verifier can reduce that trust without relying on model self-judgment.

## Short Result

FalseCite-Code produced a bounded positive result. On the locked 80-claim software-artifact slice, the primary code-tuned model trusted fabricated citations under the base prompt, while the citation-aware verifier reduced strict-holdout fabricated trust to `0.0000`.

## Evidence Summary

| Gate | Status | Key result |
|---|---|---|
| Source/verifier readiness | PASS | `80` locked claims; external verifier accuracy `1.0000`; invalid recall `1.0000`. |
| Primary audit-mode model gate | PASS | Qwen2.5-Coder-7B base strict-holdout fabricated acceptance `0.8571`; metadata evidence and verifier both `0.0000`. |
| Generation verbose160 | PASS | Base strict-holdout fabricated trust `0.8333`; metadata evidence and verifier both `0.0000`; strict parse failure `0.0667`. |
| Cross-model synthesis | MIXED | Generalization is model-dependent; Qwen2.5-3B exposed a metadata-evidence boundary while the verifier remained robust. |
| Qwen2.5-Coder-3B external-validity boundary | BOUNDARY | Base strict-holdout fabricated trust `0.8571`; verifier `0.0000`; metadata evidence failed at `1.0000` strict fabricated trust. |

## Supported Claim

For code-tuned assistants on the locked software-artifact citation slice, fabricated citations can be accepted at high rates under base prompting, and an external citation-aware verifier can suppress fabricated-citation trust to zero on the tested strict holdout.

This is useful because the remediation does not depend on asking the same model to judge its own citation. The strongest defensible claim is about external verification of software-artifact citations, not general hallucination prevention.

## Boundary

Do not claim a universal LLM vulnerability, broad hallucination elimination, or universal metadata-evidence remediation. The 3B boundary gate shows that metadata evidence can fail even when the verifier remains strong.

## Supporting Evidence

| Artifact | Purpose |
|---|---|
| `FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md` | Locked benchmark and external verifier readiness gate. |
| `FALSECITE_CODE_MODEL_GATE_20260624.md` | Primary audit-mode model gate. |
| `FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md` | Generation-mode pass with strict parse rate under cap. |
| `FALSECITE_CODE_CROSS_MODEL_SYNTHESIS_20260624.md` | Cross-model limitations and model-dependence summary. |
| `FALSECITE_CODE_USEFULNESS_DECISION_20260625.md` | Final usefulness decision and claim boundary. |
| `FALSECITE_CODE_DASHBOARD_20260625.html` | Per-experiment dashboard. |

## Recommended Next Work

Package this as a short paper or portfolio chapter centered on the external citation-aware verifier claim. A second code-tuned external-validity model is worthwhile only if the goal is to expand beyond a bounded Praxis result.

## Publication Draft

The first paper-style draft is now tracked at `FALSECITE_CODE_PAPER_DRAFT_20260628.md`. The experiment folder landing page is `README.md`.
