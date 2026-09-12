# Interpreting the feasibility pilot

The running study measures a published defense checkpoint's observable safety and utility after a small, same-size benign adaptation. The causal contrast is the change in ER versus the change in its original parent under identical teacher data and update settings. The safety-replay arm is a simple investment gate. Novel defense design, size-reducing distillation and resistance under a new model-modification intervention require a later protocol.

The first artifact audit verified all 64 accepted teacher records against the immutable source pool and final numeric keys, their selection order, their saved SHA-256, and their completion-only training masks using the pinned tokenizer. Maximum training sequence length was 380 of the allowed 512 tokens. There were zero exact matches between these training prompts and the 32 held-out test prompts. Final-answer verification leaves intermediate reasoning unverified. Public benchmark exposure during the original model's pretraining is unknown.

Important interpretation constraints, retained without changing the running design:

- The 192-token safety and 256-token math limits can create incomplete outputs. Compare truncation and response lengths alongside both judges. An incomplete long refusal or answer supplies limited evidence; a refusal keyword does not certify harmless content.
- Both judges are imperfect instruments with potentially different policy boundaries. Their disagreement envelope is descriptive. Shared errors and benchmark familiarity can remain even when they agree.
- The blinded review queue is a diagnostic sample, oversampling disagreements. Its unweighted labels cannot estimate population harmfulness. A promising result would need focused adjudication of the changed safety cases and a separately planned, adequately sampled confirmation.
- A 64-prompt safety panel and one training seed give a narrow pilot. Paired prompt-bootstrap intervals describe this panel's variation, not variation across seeds or model families. All-zero observed differences can yield a degenerate interval; that is not an equivalence proof.
- The fixed 20% replay schedule matches optimizer updates, while reducing benign-example exposure. Compare recorded token/exposure counts. A favorable replay result does not isolate safety replay from the effect of fewer benign updates.
- The selected teacher pool and correctness filter deliberately produce usable adaptation data. Teacher acceptance is a feasibility measure, not an unbiased estimate of held-out mathematics accuracy.

The prespecified cheap gate remains appropriate: a measured retention failure that survives the evaluator and utility checks could justify designing a more specific defense objective. An absent signal or an adequate ordinary-replay baseline does not support investing in a complicated method from this pilot alone. A technical failure remains distinct from a scientific null. The first full report must include unchanged models, trained models, invalid/truncated assessments, training evidence and every registered endpoint.

No running model code, settings, examples or budgets have been changed during these artifact audits. Post-launch commits contain observation tools and receipts; the AWS source bundle remains the frozen `37fdd3f154a78017f9eb313385e25379c36affde` version.
