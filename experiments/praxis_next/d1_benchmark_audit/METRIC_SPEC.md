# D1 native-label paired metric specification

This module performs **no model fitting, result generation, threshold selection, or scientific protocol freezing**. Dataset qualification must establish actual label meanings, benign status, row identities and source groups before using it. Author technique labels are not automatically benign/attack truth.

## Minimal API

```python
from experiments.praxis_next.d1_benchmark_audit.paired_metrics import (
    LabelSchema, PredictionBatch, stage_metrics,
    make_group_bootstrap_plan, paired_comparison,
)

# Use this source's native values and meanings; do not remap unrelated stages.
schema = LabelSchema({3: "Benign", 7: "Movement", 9: "Export"}, benign_label=3)
baseline = PredictionBatch(row_ids, y_true, old_predictions, schema, campaign_ids)
candidate = PredictionBatch(row_ids, y_true, new_predictions, schema, campaign_ids)
plan = make_group_bootstrap_plan(
    row_ids, campaign_ids, group_unit="author_execution_id",
    n_resamples=2000, seed=20260923,
)
result = paired_comparison(baseline, candidate, bootstrap=plan, confidence=.95)
# Reuse the same plan for other model contrasts within this fitting seed.
```

`stage_metrics(y_true, y_pred, *, schema)` evaluates one native multiclass decision vector. `paired_comparison(baseline, candidate, *, bootstrap=None, confidence=.95, include_replicates=False)` returns the two metric objects, candidate-minus-baseline differences and optional group intervals. `resample_group_indices(group_ids, sampled_groups)` exposes whole-group row repetition for independent verification.

Native IDs and row/group IDs must be nonempty strings or integers; nulls, floats, Booleans, unknown classes and ambiguous meanings are rejected. Literal integer 0 is **not** assumed benign. Ordered row IDs, native meanings, benign mapping, truth values and group assignments must match across methods. Align rows explicitly upstream: the helper never silently sorts, drops unmatched observations or maps one dataset's stages onto another's. Duplicate original row IDs are rejected.

## Definitions

Let `b` denote the explicitly declared benign label. For each true attack stage `s`, with support `N_s`:

| Quantity | Definition |
|---|---|
| Exact-stage recall | `count(y=s and prediction=s) / N_s` |
| Warning recall | `count(y=s and prediction!=b) / N_s` |
| Attack-to-benign count | `count(y=s and prediction=b)` |
| Wrong-attack-stage count | `count(y=s and prediction!=b and prediction!=s)` |
| Stage F1 | `2*correct / (true support + number predicted as s)` |
| Benign false-alert rate | `count(y=b and prediction!=b) / count(y=b)` |

Warning recall is stage-conditioned **any-attack recall**. Calling an export event movement is an exact-stage error but still an attack warning. Calling it benign loses that warning. The counts partition each supported true attack stage into exact recognition, another attack label and benign prediction. Global attack-to-benign and wrong-stage counts sum the native attack stages.

If a declared true class has zero support, its exact recall, warning recall and F1 are `None` (JSON `null`), even when a model predicts that label. Counts remain zero; unsupported precision can be zero when false predictions exist, while precision is null if there are no predictions. Benign false-alert rate is null when no true benign rows exist.

`macro_f1` is the unweighted mean F1 over the **fixed declared native schema**. It is null if any declared true class is unsupported; `macro_f1_unsupported_classes` lists them. This deliberately avoids silently changing the macro denominator or inserting zero for an absent class. When all declared classes have true support, it matches ordinary fixed-label macro-F1. It is not an observed-label-only macro score.

## Paired changes and sign reversal

All deltas are **candidate minus baseline** on identical ordered row IDs. The output includes macro-F1, benign false-alert rate, per-stage F1, exact recall and warning recall, plus changes in missed-attack/wrong-stage counts. A positive F1/recall delta is favorable; a positive false-alert or missed-attack count delta is unfavorable.

For each stage, `macro_f1_up_warning_down` identifies a positive macro-F1 delta accompanied by a negative warning-recall delta. `macro_f1_warning_sign_reversal` also identifies the reverse directional combination. Comparisons use numerical tolerance `1e-12`. Undefined input metrics produce null sign-reversal indicators, not a false assertion of agreement. A zero delta is not a sign reversal.

## Paired source-group bootstrap

A plan binds ordered original row IDs, their declared group IDs, the named source grouping unit and a fixed random seed. Every replicate samples `G` whole groups with replacement from `G` distinct source groups. Both methods and every contrast sharing the plan use **exactly the same draws**. Repeated groups repeat all their rows and counts; unequal group sizes retain their actual row weights. The statistic is event-weighted after cluster resampling, not an unweighted mean of per-group scores.

The implementation aggregates paired confusion matrices within groups and repeats these matrices by sampled multiplicity. This is exactly equivalent to explicitly repeating paired rows, while keeping 2,000-draw calculations practical. The plan can be reused across methods for one fitting seed; never pool repetitions of the same rows across fitting seeds as independent observations. `paired_draws_sha256` records shared draws; optional replicate output makes their arithmetic inspectable.

Intervals are percentile intervals of the **paired differences**, not differences of two independently bootstrapped intervals. Each interval reports valid/undefined replicate counts. A replicate lacking a target stage contributes null to that stage's recall/F1 difference. Macro-F1 needs all declared true classes in that replicate. Quantiles use only defined replicates and set `conditional_on_required_label_support=true` and `status=SUPPORT_CONDITIONAL` whenever exclusions occur. With fewer than two defined replicates, bounds are null and status is `INSUFFICIENT_DEFINED_REPLICATES`. Never describe a support-conditional interval as unconditional coverage.

Missing groups, an unnamed grouping unit, fewer than two source groups, unknown group draws or plans bound to different rows are rejected for group intervals. Point comparisons remain available without a plan. The caller must justify whether the source groups are independent campaigns/executions. This API cannot turn capture fragments, repeated recipes, generated IDs or one campaign into independent attacks; the returned independence note makes that limitation explicit.

## Validation

Tests cover a real metric sign reversal, nonzero benign native IDs, unsupported stages and absent benign rows, incompatible label meanings/row identities/truth/groups, whole-group repetition with unequal sizes, rare-stage bootstrap exclusions, and reuse/reversal of identical paired draws. Independent scikit-learn F1 calculations over explicitly repeated rows verify the sufficient-statistic implementation. No real experiment outcomes are used by these tests.
