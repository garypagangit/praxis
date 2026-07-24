# PX-057 Final Praxis Report

## Decision

**GO for H4 replication.** Gate 2 is valid and positive; H1-H3 passed. Do not claim large-scale or general robustness yet.

## Headline evidence

- Adaptive accuracy: 91.0% (182/200)
- Fixed-long accuracy: 61.5% (123/200)
- Mean generated-token saving: 66.5% (95% bootstrap CI 63.7%-69.1%)
- Prevention: 60/67 events, 89.6% (95% bootstrap CI 82.1%-95.5%)
- Early-stop harm: 1/200, 0.5%
- Integrity: 200 unique questions, 200 complete traces, 1,600 unique question-round outputs

## Critical nuance

Adaptive and answer-stability arms tied at 91.0%. Stability is the demonstrated signal; confidence adds no measured accuracy benefit in this run.

## Next investment

Run H4 on a second open model and a non-math corpus without test-set retuning. Keep the stability-only control and add latency, GPU-seconds, and dollar cost.

## Original literature

[Zhou et al. (2026), When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling](https://aclanthology.org/2026.findings-acl.1199/)
