# Frontier Batch Gate Synthesis

Date: 2026-06-19

Scope: EXP03, EXP04, and EXP05 continuation after EXP02 was parked.

## Executive Decision

EXP04 is the best next candidate, but it is not publication-ready yet. The controlled KG smoke gate passed cleanly, while the AWS HaluEval NLI gate showed that plain NLI is too weak on the strict dialogue holdout. EXP03 and EXP05 are now organized and ready for environment/agent smoke work, but neither has a performance result.

## Results

| Experiment | Gate | Status | Key evidence | Decision |
|---|---|---|---|---|
| EXP04 | Controlled KG smoke | PASS | `20` dialogues, `60` claims, KG evidence coverage `1.0000`, hallucination F1 `1.0000`, turn-3 minus turn-1 `0.2500` | Keep; measurement path works |
| EXP04 | AWS HaluEval NLI | MIXED | strict dialogue holdout F1 `0.6878`, lexical F1 `0.6723`, delta `+0.0156` | Do not promote; plain NLI is not enough |
| EXP03 | VLA source gate | PASS / SIM PENDING | `4` repos, `5` HF models, `1` public LIBERO dataset path, `48` instruction rows | Ready for simulator install smoke |
| EXP05 | World-model source/wrapper gate | PASS / AGENT PENDING | `4` repos, `2` PyPI packages, `4` perturbations, `0` shape failures | Ready for environment/agent rollout smoke |

## Internal Defensibility Challenge

| Challenge | Answer |
|---|---|
| Did we get a new publishable result? | Not yet. EXP04 has the strongest path, but the external verifier gate is mixed. |
| Did we use AWS where useful? | Yes. EXP04 HaluEval/NLI ran on AWS GPU; the instance was stopped afterward. |
| Are EXP03/EXP05 real results? | No. They are readiness gates with frozen manifests and explicit next blockers. |
| What is the most defensible next action? | Build a stronger EXP04 verifier with entity/claim extraction plus KG/text evidence, then rerun strict HaluEval/HotpotQA holdouts. |
| What should not happen next? | Do not spend large GPU time on EXP03/EXP05 until their environment smoke commands are pinned and expected to finish unattended. |

## Next Queue

1. EXP04 verifier upgrade: entity/claim extraction and KG/text evidence reranker.
2. EXP03 AWS simulator install smoke: LIBERO plus OpenVLA-OFT, one official eval command.
3. EXP05 clean/perturbed rollout smoke: Crafter or Craftax with frozen wrappers.
4. EXP02 remains parked until safe-response over-blocking is directly targeted.

Primary artifacts:

- `runs/frontier-exp04-kg-hallucination-smoke-20260619/EXP04_KG_SMOKE_GATE_RESULT_20260619.md`
- `runs/frontier-exp04-halueval-nli-full-20260619/EXP04_HALUEVAL_NLI_GATE_RESULT_20260619.md`
- `runs/frontier-exp03-vla-source-gate-20260619/EXP03_VLA_SOURCE_GATE_RESULT_20260619.md`
- `runs/frontier-exp05-worldmodel-source-gate-20260619/EXP05_WORLDMODEL_SOURCE_GATE_RESULT_20260619.md`
