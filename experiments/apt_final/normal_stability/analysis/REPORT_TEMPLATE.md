# Normal-reference stability under missing relationships

> **Unfilled report template.** Replace every bracketed field with audited evidence. Do not treat expected counts or decision examples as measured outcomes. This analysis document is outside the frozen executable inventory.

## Decision in plain language

**[COMPLETED / INCOMPLETE]. [GO FOR FURTHER DEVELOPMENT / NO-GO FOR THIS FIXED FAMILY / NO SCIENTIFIC DECISION].**

[One sentence: whether any fixed detector kept false alerts low and detected enough annotated malicious entities across both datasets, all folds, seeds, and conditions.]

[A separate sentence: whether adding masked normal examples improved the result enough to pass the registered repair screen. A detector-readiness pass alone is not a positive repair result.]

## Problem and hypothesis

When recorded relationships disappear, ordinary computer activity can look unfamiliar to a detector and trigger false alerts. We tested whether normal examples with missing relationships could reduce those false alerts while preserving detection of annotated malicious entities.

## What was tested

- Data: the existing static CADETS and THEIA graphs prepared by the MAGIC authors and normalized through our audited adapter.
- Four fixed normal-data folds per dataset: two graph files for fitting, one for calibration, and one for normal validation.
- Fresh MLP/GIN encoders: three encoder seeds crossed with three independent reference-bank seeds; local-feature kNN as a simple control.
- Three strategies: clean reference/calibration; clean reference with pooled calibration; pooled reference and calibration. Each uses the same 8,192 source rows, k=10, and the fixed 1% calibration rule.
- Clean graphs and removal of 50% of retained relationships. All normal fitting and calibration precede this run's test-label access.

Expected inventory: 1,296 logged records per phase and 1,008 unique records after local-feature duplicate accounting. **Observed and audited:** [counts and audit artifact link]. Repeated seeds and overlapping folds are not independent campaigns.

## Measured results

Provide a complete per-candidate appendix; the table below is a summary, not permission to omit failed arms. Percentages refer to entities, not attack campaigns.

| Dataset | Representation / strategy | Worst normal FPR | Worst test-negative FPR | Lowest malicious-entity recall | Mean clean / masked F1 | Ready in every repeat? |
| --- | --- | --- | --- | --- | --- | --- |
| CADETS | [candidate or none] | [measured] | [measured] | [measured] | [measured] | [yes/no] |
| THEIA | [candidate or none] | [measured] | [measured] | [measured] | [measured] | [yes/no] |

**Readiness:** normal FPR <=2%, test-negative FPR <=2%, and recall >=50%, in every fold, seed pair, and clean/masked condition. The same representation/strategy must pass on both datasets for a general result.

**Repair impact:** [measured clean F1 change against the pinned historical comparator; measured masked F1 change against each current clean-strategy representation, including the strongest one; any clean-data loss]. The registered +0.05 F1 screens remain unchanged. The historical comparison uses a different training split and is descriptive. Report paired mean/range and failed-repeat counts without treating repeats as independent observations.

**Audit and execution:** [independent audit status, exact checks and any sampling limits]; [software-test artifact]; [registration and code/data hashes]; [elapsed time]; [observed compute estimate with exclusions]; [verified AWS stop receipt]. A worker exit code alone is not an independent scientific audit.

## Interpretation

Choose the applicable conclusion, supported by the full table:

- **Ready detector and positive repair:** the fixed augmentation procedure has practical development value on these prepared graphs. It still needs independent confirmation and a separate novelty assessment.
- **Ready detector, no positive repair:** a detector is useful under this screen, but the study does not support augmentation as an improvement.
- **No candidate ready:** close this fixed family. Identify whether the failure was normal false alerts, inadequate malicious-entity recall, unstable repeats, or a combination. This does not prove that all graph methods are ineffective.
- **Incomplete execution or audit:** retain completed evidence, name what is missing, and issue no scientific go/no-go claim. Any continuation keeps the registered scientific settings and candidate inventory intact.

## Practical value and novelty are separate

A practical improvement means the measured system solves this declared detection problem better under its fixed constraints. A novel praxis contribution additionally requires a clearly differentiated method or defensible new empirical finding relative to existing research. Existing work already covers graph augmentation and missingness-aware calibration; passing this experiment alone does not establish novelty. See the checked [literature and design assessment](../../embedding_baseline/results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md).

The existing graphs can support reproducible comparisons of annotated-entity detection, normal-score stability, and controlled relationship removal. They cannot establish source-entity independence, campaign generalization, detection delay, real sensor-loss identification, analyst workload per day, or APT actor attribution. Missing UUIDs/timestamps, incomplete negative annotation, and earlier test exposure remain limitations. Relevant external evidence is documented in [HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md).

**Closure:** [state what was completed, the fixed-family decision, and which broader claims remain unsupported]. Do not reopen another dataset project or add a new checker as a condition of closing this experiment.
