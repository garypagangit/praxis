# FalseCite-Code Usefulness Decision

Date: 2026-06-25

Status: **USEFUL BOUNDED POSITIVE**

## Thesis

Code-assistant models can be induced to trust fabricated software-artifact citations, but strict package/repository metadata evidence and an external citation-aware verifier can reduce that trust without relying on model judgment.

## Decision Evidence

| Gate | Status | Key result |
|---|---|---|
| Source/verifier readiness | PASS | 80 locked claims; external verifier accuracy 1.0000 and invalid recall 1.0000. |
| Primary audit-mode model gate | PASS | Qwen2.5-Coder-7B base strict-holdout fabricated acceptance 0.8571; metadata evidence and verifier both 0.0000. |
| Cross-model synthesis | MIXED | Generalization is model-dependent; Qwen2.5-3B over-refused and Phi-3.5 was protocol-invalid. |
| Generation verbose96 | FAIL | Strong signal, but strict parse failure 0.2000 exceeded the cap. |
| Generation tight repair | FAIL | Parse fixed, but the prompt caused over-refusal and removed the vulnerability under test. |
| Generation verbose160 | PASS | Base strict-holdout fabricated trust 0.8333; metadata evidence and verifier both 0.0000; strict parse failure 0.0667. |

## Current Claim

FalseCite-Code is useful as a bounded Praxis result for `Qwen/Qwen2.5-Coder-7B-Instruct` on the locked 80-row software-artifact citation slice. The supported claim covers both audit-mode and generation-mode citation trust, plus remediation through metadata evidence and a citation-aware verifier.

## Boundary

Do not claim a universal LLM vulnerability or broad hallucination prevention. The cross-model checks show that model behavior and prompt compatibility matter.

## Next Experiment Handoff

Move FalseCite-Code into paper/chapter packaging and choose the next portfolio experiment from the dashboard queue. The strongest immediate follow-up is not another rescue run; it is external-validity expansion with a pre-registered second code-tuned model or a new portfolio experiment if publication packaging is the priority.
