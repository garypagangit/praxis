# PX-057-PX-061 Portfolio Audit

Date: 2026-07-24

## Claim rule

No experiment is classified as positive until its preregistered scientific gate
has run on frozen, non-fixture data. Smoke tests establish harness operation only.
Developmental results may repair implementation defects but may not silently
change a frozen confirmatory threshold.

## Current determinations

| Experiment | Evidence state | Determination | Permitted claim |
|---|---|---|---|
| PX-057 Adaptive Stopping | Complete valid 200-item, 1,600-generation Gate 2 | Positive for H1-H3 | Adaptive stopping reached 0.91 accuracy, saved 66.5% compute, prevented 89.6% of observed overthinking events, and harmed 0.5%; H4 transfer remains pending |
| PX-058 XAI Explanation Drift | Complete valid CICIDS2017 Gate 2 across five seeds, three methods, and five holdouts | Mixed: H1 positive, H2 negative | Top-10 global explanations were seed-stable for permutation, TreeSHAP, and LIME; explanation drift did not consistently warn of held-out failure |
| PX-059 Uncertainty-Adaptive EAGLE | Source/novelty gate completed | Closed, negative as a new Praxis candidate | The proposed contribution is materially overlapped by EAGLE-2, SpecDec++, CAST, and SpecKV |
| PX-060 Continuous Edge Direction GNNs | Complete valid 18-condition multi-seed perturbation gate | Final negative | Prediction improved and edge reversal was tolerated, but signed direction recovery was seed-ambiguous and 10% edge deletion caused about 143% relative MSE degradation |
| PX-061 Wavelet DP Federated Learning | Mechanism audit passed; corrected private adaptive development and preregistered three-band repair completed | Final negative | Unequal allocation reduced theoretical coefficient variance at matched accounting, but the FL utility improvement missed the preregistered mean-gain threshold |

## Reproducibility controls

- Frozen configurations are stored under `configs/`.
- Scientific outputs are stored under experiment-specific directories in
  `reports/`.
- Released upstream implementations are hash-pinned where used.
- Failed and superseded developmental runs remain preserved.
- Privacy comparisons in PX-061 use matched zCDP accounting.
- PX-057 Gate 2 must contain exactly 200 traces and 1,600 raw generations before
  adjudication.
- PX-060 must cover all preregistered seeds, perturbations, and learned/fixed
  direction conditions before adjudication.

## Mechanical consistency check

On 2026-07-24, all 14 relevant registry/configuration JSON files parsed
successfully and the PX-057, PX-058, PX-060, and PX-061 runners and independent
adjudicators passed Python bytecode compilation. PX-060 independently reverified
upstream commit `5e88be92c22754f022add14ba3b8c5a5e22603c5` and dataset SHA-256
`a0f793805b1fc66c6d71f48902b81ee3c80fb118d9ca86fc899a30d03cc5a0bd`.

## Remaining completion gates

All PX-057 through PX-061 source or scientific gates are now terminal and
adjudicated. PX-057 H4 is explicitly future replication work, not an incomplete
part of the completed Gate 2.

## Portfolio status

One strong bounded positive (PX-057), one mixed result with a confirmed
subhypothesis (PX-058), two final negatives (PX-060 and PX-061), and one
novelty-gate closure (PX-059). PX-057 is the leading Praxis candidate, subject
to its explicit cross-model and cross-domain transfer boundary.
