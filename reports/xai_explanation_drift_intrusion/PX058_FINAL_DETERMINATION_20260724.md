# PX-058 Final Determination

Date: 2026-07-24

## Decision

**Valid Gate 2 with a mixed result: H1 confirmed; H2 rejected.**

The completed result contains all 15 seed/method reference records and all 90
seed/method/domain records. The five seeds were all within the frozen 0.02
reference balanced-accuracy tolerance. Dataset size, pinned mirror SHA-256,
eight extracted CSVs, deterministic replay, and the label-shuffle control all
passed the independent completeness checks.

The preregistered method-consensus overall gate fails because explanation drift
did not reach the 0.40 warning threshold for any of the three methods.

## H1: seed stability

| Explanation method | Mean top-10 Jaccard | Threshold | Decision |
|---|---:|---:|---|
| Permutation importance | 0.8909 | >= 0.50 | Pass |
| TreeSHAP | 0.8212 | >= 0.50 | Pass |
| LIME | 0.6942 | >= 0.50 | Pass |

All three methods also had positive whole-rank stability: 0.9836 for
permutation, 0.9755 for TreeSHAP, and 0.7359 for LIME.

## H2: drift as a held-out failure warning

H2 was recomputed across only the five preregistered independent holdouts after
averaging the five seed repetitions within each holdout.

| Explanation method | Drift/error Spearman | Threshold | Decision |
|---|---:|---:|---|
| Permutation importance | 0.3000 | >= 0.40 | Fail |
| TreeSHAP | -0.6708 | >= 0.40 | Fail |
| LIME | -0.7071 | >= 0.40 | Fail |

Permutation drift moved in the hypothesized direction but missed the frozen
threshold. TreeSHAP and LIME moved strongly in the opposite direction. The
confidence-drift and raw feature-mean baselines were also negative (-0.50), so
none supplied a useful monotonic warning in this five-holdout design.

## Scientific interpretation

The positive result is narrow but reproducible: accuracy-matched random-forest
NID models produced stable global top-feature narratives across seeds for all
three explanation methods on this frozen CICIDS2017 design.

The proposed operational extension did not work. Cross-domain explanation
drift was method-dependent and did not consistently rank held-out detection
failure. Stable explanations across random seeds therefore should not be
conflated with explanations that warn about domain-shift failure.

## Permitted claim

On the pinned CICIDS2017 machine-learning archive, five accuracy-matched
random-forest seeds achieved preregistered top-10 global-explanation stability
for permutation importance, TreeSHAP, and LIME. Explanation drift did not meet
the preregistered held-out failure-warning threshold. These results do not
establish causal correctness, analyst usefulness, model-family
transportability, or H3 incremental warning.

## Praxis recommendation

Retain the explanation-stability result as a defensible positive subfinding,
but do not select the broader “explanation drift as an early warning” thesis as
the single strongest Praxis without a new mechanism and independent
preregistration. A follow-up should increase the number and severity range of
independent shifts and test a method-normalized drift measure; it must remain a
new experiment rather than a repair of this failed H2.
