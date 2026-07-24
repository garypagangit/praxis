# PX-062 Skill Ecosystem Provenance and Registry Hallucination

Working Praxis report - July 24, 2026

## Current status

- Gate 0: PASS on 180 inert implementation cases.
- Gate 1: VALID NEGATIVE for provenance-only defense against authentic poisoned skills.
- Gate 2: RUNNING; no live-model result yet.
- Cloud job: `px062-skill-hallucination-2026-07-24-22-21-01`

## Gate 1 result

| Condition | N | Admitted | Rate |
|---|---:|---:|---:|
| Authentic signed poison | 1,070 | 1,070 | 100.0% |
| Tampered poison | 1,070 | 0 | 0.0% |
| Nonexistent skill | 1,070 | 0 | 0.0% |
| Clean exact skill | 44 | 44 | 100.0% |
| Tampered clean skill | 44 | 0 | 0.0% |

Provenance proves identity and integrity, not semantic safety.

## Gate 2 frozen design

- Models: Qwen2.5-7B-Instruct and Mistral-7B-Instruct-v0.3
- Tasks: 300 per condition
- Conditions: open-ended, registry-constrained, post-generation verification
- Expected outputs: 1,800
- Gates: nonexistent attempted-load rate <= 1%; known-skill accuracy loss <= 5 percentage points; completeness >= 99%

## Gate 2 results

Status: **Pending cloud completion and independent adjudication.**

Populate model-condition metrics only from the sealed score artifact:

| Model | Condition | Accuracy | Nonexistent-name rate | Nonexistent-attempt rate | Abstention |
|---|---|---:|---:|---:|---:|
| Qwen2.5-7B-Instruct | open-ended | Pending | Pending | Pending | Pending |
| Qwen2.5-7B-Instruct | registry-constrained | Pending | Pending | Pending | Pending |
| Qwen2.5-7B-Instruct | post-verification | Pending | Pending | Pending | Pending |
| Mistral-7B-Instruct-v0.3 | open-ended | Pending | Pending | Pending | Pending |
| Mistral-7B-Instruct-v0.3 | registry-constrained | Pending | Pending | Pending | Pending |
| Mistral-7B-Instruct-v0.3 | post-verification | Pending | Pending | Pending | Pending |

## References

- [Original paper](https://arxiv.org/abs/2604.03081)
- [Released PoisonedSkills dataset](https://doi.org/10.5281/zenodo.19281322)
- [OpenAI skills catalog](https://github.com/openai/skills)
