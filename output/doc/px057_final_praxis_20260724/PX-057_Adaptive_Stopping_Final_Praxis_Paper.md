# PX-057: Adaptive Stopping to Prevent LLM Overthinking

Final Praxis paper - July 24, 2026

## Final determination

PX-057 is a valid positive Gate 2 result. On a frozen 200-item GSM8K sample with Qwen2.5-7B-Instruct and an eight-round iterative reconsideration protocol, the adaptive policy achieved 91.0% accuracy versus 61.5% for fixed-long inference, saved 66.5% of generated tokens, prevented 60 of 67 observed correct-to-wrong events, and harmed 1 of 200 questions.

## Registered results

| Gate | Threshold | Result | Decision |
|---|---:|---:|---|
| Accuracy delta vs. fixed-long | >= -1.0 pp | +29.5 pp | PASS |
| Mean generated-token saving | >= 20% | 66.5% (95% bootstrap CI 63.7%-69.1%) | PASS |
| Overthinking prevention | >= 25% | 89.6%; 60/67 (95% bootstrap CI 82.1%-95.5%) | PASS |
| Early-stop harm | <= 2% | 0.5%; 1/200 | PASS |

## Arm outcomes

| Arm | Accuracy |
|---|---:|
| Fixed-long, round 8 | 61.5% |
| Fixed-short, round 2 | 88.0% |
| Uncertainty-only | 88.0% |
| Answer stability | 91.0% |
| Adaptive | 91.0% |
| Oracle best step (descriptive) | 95.0% |

## Interpretation

The strongest demonstrated fact is that repeated reconsideration through round 8 degraded many initially correct answers and that a preregistered stability gate avoided most degradation. Adaptive stopping tied answer-stability stopping, so the confidence condition did not add measurable accuracy in this run.

## Claim boundary

This result applies to one 200-item GSM8K sample, Qwen2.5-7B-Instruct, greedy decoding, and one iterative prompting protocol. H4 cross-model and cross-domain transfer remains pending. No large-scale or general robustness claim is supported.

## Literature

- Zhou et al. (2026), [When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling](https://aclanthology.org/2026.findings-acl.1199/) - original publication and PDF.
- Snell et al. (2024), [Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters](https://arxiv.org/abs/2408.03314).
- Muennighoff et al. (2025), [s1: Simple test-time scaling](https://arxiv.org/abs/2501.19393).
- Cobbe et al. (2021), [Training Verifiers to Solve Math Word Problems](https://arxiv.org/abs/2110.14168) - GSM8K source.
- Qwen Team (2024), [Qwen2.5 Technical Report](https://arxiv.org/abs/2412.15115).

## Recommended next gate

Freeze an H4 replication matrix with a second open model and a non-math reasoning corpus, retain all comparison arms, add real latency/GPU/cost measurements, and require confidence to improve over stability-only before keeping it in the production policy.
