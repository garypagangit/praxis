# Q1 amendment A1: upstream effective epoch count

September14,2026, before any pretrained-model inference. This amendment supersedes only the phrase “one optimization epoch” as a description of the effective upstream W1ACAS computation. The frozen Q1 document and original freeze receipt remain intact. No cohort, prediction, significance threshold, or efficacy criterion changes.

Independent source review found that `w1acas.py` passes `n_epochs=1`, but the constructor in `conformal.py` supplies default `epochs=2`; its `predict` method reads `epochs`. Consequently the pinned official code executes two optimization epochs despite the caller requesting one. This is an upstream parameter-name mismatch.

Decision: preserve the original implementation in the base reproduction. Report `requested_n_epochs=1`, `effective_epochs=2`, and `upstream_epoch_parameter_mismatch_preserved=true` in the actual receipt. The worker asserts the effective value before inference. Any future corrected one-epoch variant must have a separate name, source freeze and results. We do not silently repair the published algorithm or label its runtime as one effective epoch.

The original synthetic W1ACAS controls also exercised the same effective two-epoch implementation. Their purpose was chronology and finite-score validation, not comparison of optimization budgets. No pretrained model was used in those controls.
