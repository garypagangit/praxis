# PX-059 Source Gate — Uncertainty-Adaptive Speculative Decoding

Date: 2026-07-24
Decision: **DO NOT RUN AS PROPOSED — novelty gate failed**

## Proposed hypothesis

Use draft-model uncertainty to adapt EAGLE speculation depth or tree size, reducing rejected work while preserving lossless target-model output.

## Literature determination

The proposed mechanism is not a new extension:

- EAGLE-2 already uses calibrated draft confidence to construct context-dependent dynamic draft trees.
- SpecDec++ already learns acceptance probabilities and stops candidate drafting with a threshold policy.
- CAST already combines dynamic EAGLE trees with measured GPU and batch-size inference cost.
- SpecKV already adapts speculation length using entropy/confidence under compression.
- Recent work also evaluates calibration transfer across tasks and adaptive disable/shrink behavior.

The original PX-059 hypothesis therefore duplicates an established research direction. A positive speed result would be a replication or implementation benchmark, not a defensible new Praxis contribution.

## Evidence

- EAGLE: https://arxiv.org/abs/2401.15077
- EAGLE-2: https://arxiv.org/abs/2406.16858
- SpecDec++: https://arxiv.org/abs/2405.19715
- CAST / inference-cost-aware dynamic trees: https://openreview.net/forum?id=iaWyRYthFf
- SpecKV: https://arxiv.org/abs/2605.02888
- Official EAGLE implementation: https://github.com/SafeAILab/EAGLE

Official implementation frozen locally at commit:

`cb7e0841fe0c206c6ed74a197ad5e2a1f13f5a2b`

## Portfolio decision

Close PX-059 before GPU expenditure. Do not count it as a failed empirical result; it is a successful source-gate rejection. Move compute to PX-060.

If retained for engineering value, label it only as an independent reproduction benchmark of EAGLE-2/CAST—not as a new Praxis experiment.
