# FalseCite-Code Source/Verifier Gate

Date: 2026-06-23

Experiment: `FALSECITE-CODE-01` - FalseCite-Code: Citation Poisoning in Code-Assistance Prompts

## Decision

Status: **PASS**

This is a source/readiness and strict-verifier gate, not yet a model-vulnerability publication claim.
The gate determines whether a defensible FalseCite-style code-artifact benchmark can be built from live public metadata before spending GPU time on LLM generations.

## Literature Anchor

FalseCite motivates fabricated-citation attacks against LLM factuality. This gate narrows that idea to software artifacts: package versions, GitHub repositories, and GitHub tags used inside code-assistant prompts.
The earlier Praxis EXP04 hallucination verifier failed because response-only artifacts beat evidence-aware features on external holdout. This experiment therefore starts with strict external metadata verification and will require response-only and trust-all baselines before any model claim is promoted.

## Research Questions and Hypotheses

| Item | Question / hypothesis | Gate |
|---|---|---|
| RQ1 / H1 | Can we construct a balanced, public, code-artifact citation-poisoning slice from PyPI, NPM, and GitHub metadata? | At least `70` claims and at least `14` strict-holdout claims. |
| RQ2 / H2 | Can a strict external verifier label valid and fabricated artifacts without model judgment? | Verifier accuracy >= `0.95` and invalid recall >= `0.95`. |
| RQ3 / H3 | Does the verifier avoid the obvious response-artifact trap? | Compare against trust-all and regex-suspicion baselines; do not promote unless verifier dominates both. |

## Dataset

The generated slice contains `80` claims.

| Split | Claims |
|---|---:|
| train | 45 |
| validation | 20 |
| strict_holdout | 15 |

| Claim type | Claims |
|---|---:|
| github_repo | 20 |
| github_tag | 20 |
| npm_version | 20 |
| pypi_version | 20 |

The split key is `artifact_id`, so paired true/fabricated versions of the same artifact stay in the same split. This prevents a later learned verifier from seeing the same package in train and strict holdout.

## Graphical Model Representation

`artifact metadata source -> clean/fabricated citation -> prompt condition -> model/verifier verdict -> strict metadata score`

The current gate evaluates the deterministic verifier branch. Later model gates may add base LLM, RAG-backed LLM, and citation-aware verifier conditions without changing the split.

## Results

| Method | Rows | Accuracy | Invalid precision | Invalid recall | Invalid F1 |
|---|---:|---:|---:|---:|---:|
| Strict external verifier | 80 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Trust-all baseline | 80 | 0.5000 | 0.0000 | 0.0000 | 0.0000 |
| Regex-suspicion baseline | 80 | 0.5000 | 0.0000 | 0.0000 | 0.0000 |

API error rate: `0.0000`.

## Strict Holdout

| Method | Rows | Accuracy | Invalid recall | Invalid F1 |
|---|---:|---:|---:|---:|
| Strict external verifier | 15 | 1.0000 | 1.0000 | 1.0000 |
| Trust-all baseline | 15 | 0.5333 | 0.0000 | 0.0000 |
| Regex-suspicion baseline | 15 | 0.5333 | 0.0000 | 0.0000 |

## Internal Defensibility Challenge

| Challenge | Answer |
|---|---|
| Is this a model result? | No. This is a benchmark/verifier readiness result. |
| Are labels derived from external sources rather than model judgment? | Yes. Labels come from PyPI, NPM, and GitHub metadata. |
| Is there a strict holdout? | Yes. Splits are keyed by artifact id. |
| Did we avoid the EXP04 response-artifact failure? | Partially. This gate includes trust-all and regex baselines, but model response-only baselines still need to run in the GPU/model gate. |
| Should this be published now? | No. Promote only after a locked LLM vulnerability/remediation gate shows a real model effect. |

## Next Action

Prepare the model gate with three conditions: base model, retrieval-backed prompt, and citation-aware verifier. Use AWS GPU once `praxis-build` SSO is refreshed.
