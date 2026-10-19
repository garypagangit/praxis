# Final Praxis experiment workspace

**Identifying Autonomous AI APT** · Owner: Gary Pagan · Created October 19, 2026

**Status: design templates prepared; protocol not frozen; collection/training not executed by this workspace.** [RQs/Hs](../../PRAXIS_RESEARCH_DESIGN.md) · [Methodology](../../PRAXIS_EXPERIMENT_PROTOCOL.md) · [Schedule](../../PRAXIS_STATUS_TRACKER.md).

## Experiment structure

| Card | Research purpose | Development experiment | Confirmation artifact |
| --- | --- | --- | --- |
| [EXP-RQ1](RQ1_FEATURES.md) | Identify discriminative feature families | Host/network comparisons, family ablations and grouped importance | Frozen contrasts and feature findings with uncertainty |
| [EXP-RQ2](RQ2_GENERALIZATION.md) | Test stable attributes and unseen-group transfer | Operator/configuration holdouts and timing/tool controls | Transfer contrasts and scope-qualified H2 decision |
| [EXP-RQ3](RQ3_MODELS.md) | Compare candidate classifiers fairly | Common features/folds and bounded tuning | Paired locked comparison, cost and H3 decision |

The cards share collection and model artifacts. Reusing the same trials for three analyses does not create three independent replications. Freeze the combined comparison family and multiplicity plan before final scoring.

## Methodology and artifact flow

| Stage | Input | Procedure / gate | Output template or artifact |
| --- | --- | --- | --- |
| Design | Problem, RQs/Hs and dataset review | Resolve feasibility and operational margins | [PROTOCOL_TEMPLATE](templates/PROTOCOL_TEMPLATE.md) |
| Preparation | Lab, operators and AI configurations | Verify matching, autonomy, scope and available groups | Protocol sections 2–4 |
| Readiness | Reset and sensor evidence | Gate A must pass before scored trials | Protocol section 4 |
| Collection | Frozen cells and randomized/counterbalanced schedule | Log every attempt, including failure and intervention | [trial template](templates/trial.template.json) |
| Data validation | Native evidence and registry | Check hashes, coverage, labels, duplicates and grouping | Data-quality report and split manifest |
| Features | Qualified training evidence | Implement family definitions; fit transforms inside training folds | [feature dictionary](templates/FEATURE_DICTIONARY.md) |
| Training | Frozen representation, folds and candidates | Fit/tune with training-only preprocessing | [run template](templates/run.template.json) |
| RQ experiments | Development outputs | Apply each card's predefined contrasts | [experiment template](templates/EXPERIMENT_TEMPLATE.md) |
| Locked evaluation | All candidates and decisions frozen | One evaluation batch; preserve every candidate's outcome | [results template](templates/RESULTS_TEMPLATE.md) |
| Delivery | Predictions and analysis | Regenerate tables; review claim boundaries | Paper, evidence index and defense figures |

## Required decisions before execution

| Decision | Owner | Due | Current state |
| --- | --- | --- | --- |
| Available humans, AI families/configurations, independent trial counts and precision rationale | Gary / Analysis | Oct 21 | Unresolved |
| Scenario cells, access window, knowledge conditions and counterbalance schedule | Human / AI / Lab | Oct 22 | Unresolved |
| Sensor loss tolerances and Gate A acceptance | Lab | Oct 23 | Unverified |
| Exact baseline per H1/H2 contrast and full/reduced feature definitions | Analysis | Oct 26 | Unresolved |
| H2 reference split, transfer-loss margin and attribute-stability summary | Analysis / Advisor | Oct 26 | Unresolved |
| H3 minimum important difference and human false-AI-label threshold if used for selection | Analysis / Advisor | Oct 26 | Unresolved |
| Folds, seeds, model versions/search budgets, confidence method and multiplicity family | Analysis | Oct 26 | Unresolved |
| Test steward, archive location, freeze commit and permitted readers | Gary / Lab | Oct 26 | Unresolved |

Use `null` in JSON templates for unresolved facts. A null is not zero, a negative result or a passed gate. Copy templates into the restricted execution workspace and complete them before use. Never commit raw logs, operator identities, credentials or confidential evidence locations to the public repository. Publish sanitized manifests, aggregates and reproducible analysis references.

## Evidence index to populate

| Evidence | Required contents | Current artifact |
| --- | --- | --- |
| Protocol freeze | Completed protocol, decisions, reviewer, commit and date | Pending |
| Collection | Trial records, matching schedule, reset/canary evidence, native-log hashes | Pending |
| Dataset validation | Counts by arm/group, exclusions, source loss, duplicate audit and partitions | Pending |
| Feature build | Dictionary, extraction version, fitted-transform provenance and schema hashes | Pending |
| Training | Every candidate/fold/seed manifest, search log, model and failures | Pending |
| Evaluation | Trial scores, labels under restricted access, contrasts and uncertainty | Pending |
| Results and audit | RQ1–RQ3 reports, claim-to-evidence map and regeneration record | Pending |

## Completion criteria

An experiment is complete when its frozen comparisons can be regenerated, all attempts/deviations are accounted for, and each hypothesis has a justified disposition: supported, not supported, inconclusive or protocol invalid. A positive finding is not required for completion. A blocked or unrun experiment remains incomplete. All planned delivery ends December 1, 2026; AI Review is due November 14.
