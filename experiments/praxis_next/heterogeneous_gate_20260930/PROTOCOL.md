# PX-093: Heterogeneous warning gates and false-alert accounting

Freeze this protocol, code, data hashes and software versions before either new fit. This is the requested A6 extension, registered separately to preserve the completed PX-092 result. No threshold or outcome in PX-092 is changed. All evaluation sources have already been examined; additional fits do not create fresh validation.

## Models and training

Exactly two new multiclass logistic-regression pipelines, one per dataset. Pipeline: median imputation fitted on training data only, StandardScaler, LogisticRegression(C=1, solver=lbfgs, max_iter=500, tol=1e-4, class_weight=None, random_state=8101). At most two numerical-library threads. Record all convergence warnings and iteration counts; do not tune after failure. A non-converged fit is reported as such and cannot qualify a successful extension.

UNRAVELED: current+roles features, same seed-8101 capped final training rows as PX-081 (12,000 benign, up to 4,000 per attack class), captures 0–4. AIT: current+history features, all eligible rows from the original six training executions, with Wilson/Harrison excluded. This is a different classifier, not new independent evidence or new attack coverage. Reuse existing seed-8101 current-only LightGBM; it needs no new fit. Reuse the three original roles experts on UNRAVELED and history experts on AIT.

## Comparisons

Eight fixed sets: base three seeds; base+current; base+LR; full five-member A6 (base+current+LR); three heterogeneous members (first base seed+current+LR); base+duplicate of its first member; LR alone; current alone. Every set gets OR, probability mean, and exfiltration-best constituent as a label-informed bound. OR stage refinement and tie rules follow PX-092. Preserve every set regardless of result.

UNRAVELED: clean, delayed/unavailable, wrong-host-history; budgets 1,2,3. Shared seed-8101 acquisition schedule, cost 1 for roles and zero for current. When roles are unavailable or late, original base members use their respective current-only fallback from PX-092; the new LR uses the existing seed-8101 current-only model. Wrong-host history does not change any selected feature and is a negative control. AIT: Wilson, Harrison and pooled, history cost 2 in simulated units, current cost zero, no simulated outage. No real operational cost claim.

## Outcomes and decisions fixed before fitting

- **H1, structural:** OR retains every constituent warning and false alerts are at most the sum of constituent counts in every cell. Duplicate control must leave OR warning decisions unchanged. A failure is a bug and halts the audit.
- **H2, clean heterogeneous benefit:** full A6 UNRAVELED clean budget 2 strictly improves exfiltration warning recall over base-three OR, retains at least 95% recall, and produces no more than twice the mean false-alert count of the *fixed original three base models*. This denominator never grows when LR is added. Report each component if the joint target fails.
- **H3, adapted external benefit:** full A6 strictly improves exfiltration warning recall over its best constituent in Wilson, Harrison and pooled; has overlap ratio below .75 in both executions; and produces no more than twice the mean false-alert count of the original three history models in each execution. These are exploratory engineering targets, not measured analyst capacity. Both new fits must converge for an affirmative recommendation. PX-092 H3 remains failed even if this later hypothesis passes.

Also report marginal attack/exfiltration warnings, marginal benign false alerts and additional false alerts per recovered exfiltration flow relative to base OR (undefined if no recovery); OR-unrecoverable attacks; OR warnings lost by mean, separated into all-members-warn versus some-members-benign; fixed-class macro-F1; exact and warning recalls; overlap ratio and model count. A falling overlap ratio alone is not evidence of useful diversity: duplicating a member increases its denominator while leaving OR decisions unchanged.

## Audit and interpretation

Independent script (no import of experiment runner) validates frozen sources, native manifests, row/label equality, training/test separation, selected rows, full LR prediction reproduction, all OR/mean decisions, all reported confusion matrices and acquisition cost on each row, membership, H1 inequalities, duplicate warning equality, and H2/H3 from the resulting counts. Preserve private models and per-row predictions, publish aggregate JSON/CSV and audit receipts. Use local CPU only; no cloud or model API.

The user-proposed strong thesis is not assumed: prior single-model remedies sometimes recovered warnings at high cost, their comparisons were not all one common randomized benchmark, and OR is not proven the only possible repair. Classical fusion and error-diversity literature precludes claiming those concepts as new. The decision is whether these measurements support a narrower Praxis, with novelty and independent efficacy still separate requirements.
