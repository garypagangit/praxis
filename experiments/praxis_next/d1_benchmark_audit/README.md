# Temporal validity and warning retention in APT-stage benchmarking

**D1 / PX-084: qualification and portable audit core completed; new detector comparisons have not run.**

This work develops the measurement praxis: determine when reported stage scores give a misleading picture of attack warnings. The measured contribution does not require inventing a winning classifier. It does require qualified data, controlled comparisons and an accurate account of prior work.

## Evidence already available

| Existing study | Actual finding | Supported conclusion |
|---|---|---|
| [PX-082 temporal comparison](../px082_temporal_audit/REPORT.md) | Same anchor and class budgets: current-feature macro-F1 increased by 0.0632 and exact movement-label recall by 35.19 percentage points with time-mixed training. | Training composition substantially changed these scores while the model architecture stayed fixed. |
| [PX-081 metric tradeoff](../px081_evidence_acquisition/INTERPRETATION.md) | Clean, maximum-budget mean macro-F1 increased from .7148 to .7379, while exfiltration-labeled rows receiving any attack warning fell from 85.18% to 76.25%. | A better aggregate score accompanied 8.93 percentage points fewer warnings on this stage. This analysis was retrospective in PX-081. |
| [PX-082 chronological history comparison](../px082_temporal_audit/REPORT.md) | Macro-F1 .7365 to .7582; movement F1 .2091 to .2836; mean benign false alerts 24.0 to 14.3. | History produced useful measured gains under past-only fitting. Exfiltration-to-benign errors also increased in every seed, so the warning tradeoff remains part of the finding. |

These are three fitting seeds on one exposed UNRAVELED campaign. The temporal anchor has 18 movement annotations, concerning author-labeled Remote System Discovery. They establish the reported measurement findings; they do not independently establish successful movement, theft, or future-incident generalization.

## What D1 adds now

- A [repository preregistration](PREREGISTRATION.md) and [machine-readable protocol](protocol.json) for the requested four-source extension, including positive, null, opposite and unavailable-result interpretations.
- A [portable split planner](temporal_plan.py) reproducing the original PX-082 anchor, both training pools and matched class counts exactly. The [compatibility receipt](PORT_VERIFICATION.json) covers 382,229 source rows and 104,051 anchor rows; this is a software check, not another experiment.
- [Paired stage/warning metrics and source-group bootstrap code](METRIC_SPEC.md), with unsupported classes and small group counts exposed.
- A fresh [source qualification inventory](DATASET_QUALIFICATION.md) and a [frozen, executed chronological support diagnostic](SUPPORT_CUTOFF_AUDIT.md).
- A [closest-work review](LITERATURE_POSITIONING.md) that identifies the actual prior hierarchy study and distinguishes the proposed measurement contribution from established metrics.

## Actual results of the requested expansion

| Requested source | Measured or verified status | Role in D1 today |
|---|---|---|
| SCVIC-APT-2021 | Local author-attributed training file: 259,120 rows, six native classes. Recorded start times permit an all-class cutoff, but 220 benign rows have 1970 dates, other rows have 2015 dates, physical-clock provenance and execution groups are unqualified, and the listed author test file is absent locally. | Recorded-time support diagnostic. No qualified temporal or independent-campaign model comparison yet. |
| DAPT2020 | 86,691 rows, five native classes, including 15 exfiltration rows. Reconnaissance finishes before exfiltration starts. No single cutoff can leave every class in both earlier fitting and later testing under the declared rule. | A completed, measurable temporal-support limitation. Useful for other explicitly designed tasks; unsuitable for an unchanged all-class PX-082 contrast. |
| DSRL-APT-2023 | 65,000 rows. Author paper describes CTGAN attacks derived from DAPT2020 and 10,000 benign rows sampled from DAPT2020. Generated time fields do not establish real event chronology. | A derivative synthetic source; cannot count as independent temporal replication. |
| S-DAPT-2026 | No qualified released data bytes were obtained. The checked arXiv record remains withdrawn; a separate SSRN record did not provide a verified corrected data release. | Availability/provenance outcome. No performance or temporal claim. |

**DAPT support result:** to have two earlier fitting examples of every native class, the cutoff must be later than July 19, 2019, 16:38:37. To retain a later reconnaissance example, it must be no later than July 17, 2019, 19:24:55. Both conditions cannot hold. This used all rows and native labels; it did not depend on selecting an arbitrary train/test percentage. Event-end requirements and duplicate purging can only make support stricter.

**SCVIC support result:** its recorded-start necessary interval is nonempty: after October 21, 2015, 10:21:12 through 22:56:16. We therefore do not claim all its possible cutoffs lack stage support. A nonempty interval does not validate the recorded clock, event availability or independent execution groups. No cutoff was chosen to maximize performance.

The support algorithm and synthetic tests were committed at `ea9956c` before reading the actual CSVs with that algorithm. The datasets themselves were already examined in earlier development work. See [full numeric bounds and source hashes](SUPPORT_CUTOFF_AUDIT.json).

## Contribution and literature position

**Proposed thesis:** APT-stage evaluation should jointly measure correct stage identification, retention of an attack warning, and benign alert workload under source-qualified temporal protocols; headline scores alone can hide consequential tradeoffs.

The contribution is the controlled measurements and reproducible audit, including which released artifacts support the claimed evaluation. The prior Uddin et al. study already reports exact attack recall and attacks classified as normal. Thus warning recall is an established confusion-matrix quantity, not a newly invented metric. See [the 2025 journal record](https://doi.org/10.1016/j.adhoc.2025.103982) and [the available author manuscript](https://arxiv.org/html/2403.13013v1).

Temporal validity and critical APT evaluation also have close precedents. D1's related-work comparison includes TESSERACT, Bilot, Guerra and the 2026 flow-based TAN-IDS framework, whose stated scope leaves multiclass/family discrimination and systematic feature ablation for later work. New controlled evidence can extend that literature; a new name or a switch from provenance to flows alone does not establish novelty.

## Next executable work and boundaries

The most direct expansion within the requested list is SCVIC: obtain source-supported timestamp interpretation, event-completion units, and original capture/run identities or a qualified author holdout. Then freeze its adapter, input manifest, boundary and execution source before new fits. A point comparison need not have multiple independent campaigns, but it must have qualified chronology; its uncertainty and generalization claims must match the available grouping.

A [final bounded check of public author sources](SOURCE_ACCESS_CHECK.md) did not resolve those missing fields. No access restrictions were bypassed.

DAPT requires a different research question, such as recognition of a stage absent from training, or another repeated execution. That would be a separately registered extension rather than an all-stage closed-set replication. DSRL can support a separately identified synthetic sensitivity analysis. S-DAPT requires an actual verified release and its documentation. None should be silently substituted for the missing independent replication.

The new generic core is a planner and metric library, not a completed four-dataset fitting executor. No requested source currently passes all requirements for the unchanged new comparison. The existing PX-082 fitter remains available, and a qualified adapter/executor is frozen only after its source contract is established.

## Validation and compute

Run core checks from the repository root:

```powershell
& C:/w/tabular_batch_env_20260921/Scripts/python.exe -m pytest experiments/praxis_next/d1_benchmark_audit -q
```

The compatibility and support receipts preserve actual outputs and their code/input hashes. No source dataset or row-level predictions are added to this repository. **D1 new model fits: 0. New AWS use/spend: 0 / $0.** The protocol caps future allocation at $5 in total and 60 minutes aggregate instance time; it does not authorize spending to work around invalid data.

Registration and source hashes: [FREEZE.json](FREEZE.json). Current status and validation receipt: [STATUS.json](STATUS.json).
