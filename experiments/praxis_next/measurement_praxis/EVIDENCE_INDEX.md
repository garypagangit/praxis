# Evidence index

This package supports **When Better APT Scores Hide Missed Attack Warnings**. Public artifacts report aggregates and computational checks; raw traces and row-linked prediction archives remain private. File hashes and input provenance identify exactly what was inspected.

## Start here

- [Word manuscript](apt_evaluation_praxis.docx), [PDF manuscript](apt_evaluation_praxis.pdf), [searchable Markdown manuscript](manuscript.md).
- [Reproduction guide](REPRODUCE.md) and [review checklist](REVIEW_CHECKLIST.md).
- [Literature and claim audit](LITERATURE_AND_CLAIMS.md), [reference metadata](references.json).
- [Final artifact verification](FINAL_VERIFICATION.json), [package manifest](PACKAGE_MANIFEST.json).

## Claim-to-evidence map

| Claim | Direct evidence | What is independently checked |
|---|---|---|
| Time-mixed fitting raises current-feature macro-F1 by .0632 and movement recall by 35.19 pp | [Original temporal metrics](../px082_temporal_audit/METRICS.json), [means](../px082_temporal_audit/SUMMARY.json), [split design](../px082_temporal_audit/DESIGN.json) | Same anchor, matched class counts, source hashes, original arithmetic audit; new per-seed paired intervals |
| Higher F1 can coexist with fewer exfiltration warnings | [All paired results](evidence/paired_reanalysis/PAIRED_RESULTS.json), [readable report](evidence/paired_reanalysis/REPORT.md), [complete CSV](evidence/paired_reanalysis/PAIRED_METRICS.csv) | 36 pairs, 66 original archives, ordered identities, all stages, paired group intervals |
| 19 of 27 acquisition comparisons show F1-up/warning-down | [Direction counts](evidence/paired_reanalysis/DIRECTION_COUNTS.json) | Every specified acquisition seed, condition and budget; correlated and duplicate scenarios disclosed |
| Clean budget-three average hides fitting-seed variation | [Per-seed results](evidence/paired_reanalysis/PAPER_SECTION.md) | Additional exfiltration-to-benign decisions: 897, 3, 22; no pooled-seed confidence claim |
| Chronological history improves F1 and reduces benign alerts while losing some exfiltration warnings | [Original means](../px082_temporal_audit/SUMMARY.json), [paired means](evidence/paired_reanalysis/MEANS.json) | Same anchor, +7/+6/+8 missed exfiltration warnings, conditional intervals |
| No all-native-class single DAPT cutoff meets the declared support rule | [Frozen necessary bound](../d1_benchmark_audit/SUPPORT_CUTOFF_AUDIT.json), [independent sweep](evidence/qualification_audit/VERIFICATION.json) | Distinct CSV parser; all 28,941 membership states; source hashes before/after reading |
| SCVIC has possible recorded-start support but unresolved chronology | [Qualification audit](evidence/qualification_audit/REPORT.md), [source-access check](../d1_benchmark_audit/SOURCE_ACCESS_CHECK.md) | 9,475 feasible recorded-start states; original clock anomalies retained |
| DSRL derives from DAPT; S-DAPT was not acquired as a qualified release | [Primary-source review](evidence/qualification_audit/SOURCE_REVIEW.json), [native class counts](evidence/qualification_audit/NATIVE_CLASS_COUNTS.csv) | DSRL paper/release/license identity; current withdrawal/access status; no invented S-DAPT counts |

## Independent computation and frozen provenance

- [Paired analysis plan](evidence/paired_reanalysis/ANALYSIS_PLAN.md), frozen at `c0d884e` before the new arithmetic, after the pattern was already observed. This is **retrospective** reanalysis.
- [Paired arithmetic audit](evidence/paired_reanalysis/AUDIT.json): 720 checked point/interval quantities and 66 unchanged prediction archives.
- [Publication arithmetic audit](evidence/paired_reanalysis/PUBLICATION_AUDIT.json): 756 checked means and direction quantities.
- [Public capture confusion counts](evidence/paired_reanalysis/CAPTURE_CONFUSIONS.json) and [shared bootstrap draws](evidence/paired_reanalysis/CAPTURE_DRAWS.json): sufficient statistics permit public recomputation of reported metrics and intervals.
- [Public-only verification](evidence/paired_reanalysis/PUBLIC_VERIFICATION.json): independent formulas operating on those released aggregates; no private predictions required.
- [Source-count verification code](evidence/qualification_audit/verify_qualification.py), frozen at `e6b5799`; [result](evidence/qualification_audit/VERIFICATION.json): all 16 registered checks passed.
- [Original four-study verification](../FINAL_VERIFICATION.json): prior source commits, original audits and 24 original tests.
- [D1 core freeze](../d1_benchmark_audit/FREEZE.json), [portable metric specification](../d1_benchmark_audit/METRIC_SPEC.md), [port receipt](../d1_benchmark_audit/PORT_VERIFICATION.json): reproduces the original anchor and pools.

## Complete supporting experiments

| Record | Status and use |
|---|---|
| [History selection](../px080_context_selector/results/REPORT.md) | Completed 39-fit development study; seven arms and all five evidence conditions retained |
| [Evidence acquisition](../px081_evidence_acquisition/README.md) | Completed 84-fit study; all budgets/conditions/policies, costs and actions retained |
| [Temporal evaluation](../px082_temporal_audit/REPORT.md) | Completed 18-fit study; fixed-anchor and separate random-row results |
| [T1105 selector transfer](../px083_policy_transfer/README.md) | Completed two-fit supplement; different target and negative-label meaning; not an independent movement/exfiltration result |
| [D1 extension](../d1_benchmark_audit/README.md) | Completed qualification and core preparation; zero new model fits; the four-source model extension remains unexecuted |

## What the package does not establish

The computational audits do not independently validate author labels or certify real theft, successful movement, early warning, cross-campaign generalization, a novel recall metric, or publication acceptance. No unexecuted Random Forest or four-dataset model result is presented as measured. The evidence is sufficient to support the bounded measurement claims in the manuscript; broader claims require additional data and experiments.
