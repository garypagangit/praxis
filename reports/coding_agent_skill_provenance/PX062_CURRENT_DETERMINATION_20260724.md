# PX-062 Current Determination

Date: 2026-07-24

> **Gate 2.1 status update, 2026-07-26:** The first Gate 2 cloud job failed at
> S3 source retrieval before user code or model inference. It produced no
> scientific result. The task hash stated below is a stale pre-run value and is
> superseded, with full disclosure, by
> `PX062_GATE2_1_1_PRERUN_ADDENDUM_20260726.md`. Gate 1 results are unchanged.

## Status

**Gate 1 valid negative for provenance-only defense against authentic poisoned skills.**

The evaluation used the authors' complete Zenodo release of 1,070 poisoned `SKILL.md` files and 44 clean `SKILL.md` files frozen from the OpenAI skills catalog at commit `49f948faa9258a0c61caceaf225e179651397431`. No skill code was executed.

## Results

| Condition | Provenance-only allow rate | Decision |
|---|---:|---|
| Authentic, correctly hashed and signed poisoned skills | 1.0000 (1,070/1,070) | Fail |
| Tampered poisoned skills | 0.0000 (0/1,070) | Pass |
| Nonexistent skills | 0.0000 (0/1,070) | Pass |
| Clean exact skills | 1.0000 (44/44) | Pass |
| Tampered clean skills | 0.0000 (0/44) | Pass |

## Interpretation

Existence checking, hash pinning, version pinning, and registry signatures verify identity and integrity. They do not establish that authenticated content is safe. The attack studied by Qu et al. can be delivered as an authentic skill published by its author; a provenance-only gate therefore admits the full released attack corpus when the malicious artifact is the signed registry object.

The deterministic gate remains useful against:

- nonexistent or hallucinated skill identifiers;
- post-publication file substitution;
- missing manifests;
- unsigned registry records;
- signer mismatch;
- version or rollback mismatch.

It is not a sufficient defense against semantic poisoning. A stronger policy must add publisher trust/review, semantic analysis, least-privilege permissions, sandboxing, or multi-model inspection.

## Skill-name hallucination extension

A frozen 300-task benchmark is ready:

- 100 known-skill tasks;
- 100 unavailable-capability tasks;
- 100 near-miss skill-name tasks;
- 43 unique registry names from the frozen OpenAI snapshot;
- three conditions: open-ended, registry-constrained, and post-generation verification.

Task SHA-256: `439761496da03ed7bec64f241e37e424040d9ff2e9df8ed79bb402aba1b2ab9d`
Registry SHA-256: `2c447b5eee07b2f2930fc8649860652b36d4902dafadfa83e3f5d7aa041a76db`

The live-model hallucination experiment has not yet run. No hallucination-rate claim is permitted until outputs from at least two frozen models are collected and scored.

## Sources

- Original paper: https://arxiv.org/abs/2604.03081
- Evaluation dataset: https://doi.org/10.5281/zenodo.19281322
- Clean registry snapshot: https://github.com/openai/skills
