# Human vs. Autonomous AI Operator Classification in APT Intrusions

**Primary project hub**, aligned on November 17, 2026 to the user-provided `Praxis_Draft_v1.6_Human_vs_AI_Operator_Classification.docx` (SHA-256 `81c3748d643def5b904ebfc0393b5d78945bb46b80f121c40e2131a1bbad99e5`). The document is a draft; its reported findings below have not been independently reproduced in this worktree. [Current status tracker](../../PRAXIS_STATUS_TRACKER.md).

## Project description

The praxis investigates whether supervised boosting classifiers can distinguish human from autonomous AI operators from telemetry on the **operator host** in an emulated APT intrusion. Its synthetic dataset contains activity performed in a constructed laboratory: nine sessions, five human and four from one AI model and harness, on the same seven-stage exercise. The primary evaluation holds out whole sessions. It does not establish operational-network performance, attribution to a real APT, or transfer to new AI families or harnesses. Target and network logs were collected in the paper but were **not** model inputs.

## Project materials

- **Paper:** [v1.6 draft](../../paper/autonomous-ai-apt/Praxis_Draft_v1.6_Human_vs_AI_Operator_Classification.docx) · [October 29 revision](../../paper/autonomous-ai-apt/Identifying_Autonomous_AI_APT_Working_Praxis_Updated_20261029.docx) · [October 24 working paper](../../paper/working-praxis-20261024/README.md). A separately approved final paper is not yet identified.
- **Presentation:** [November 13 advisor presentation, V008](../../paper/autonomous-ai-apt/Final_Defense_Idea_Advisor_Submission_V008_11132026.pptx). A final defense presentation is not yet identified.
- **Dataset and results:** [Study results and evidence](study/README.md) · [Hypothesis table](study/results/tables/T_hypotheses.csv). Raw and cleaned study data are restricted and were not in the source repository; the [earlier synthetic engineering dataset](pipeline/GROUNDED_DATASET.md) is different.
- **Code and prompts:** [Paper-specific study code](study/code/README.md) · [Redacted starting prompt](study/prompt/starting_prompt_redacted.md) · [Restricted telemetry collector](collector/README.md) · [Earlier experiment harness](pipeline/README.md).
- **Environment:** [Study Python requirements](study/requirements.txt) · [Upstream GOAD project](https://github.com/Orange-Cyberdefense/GOAD). The study-specific lab deployment code is not included in the imported repository.

Raw evidence, sensitive configuration and credentials must remain restricted; publish only reviewed, authorized materials.

## Research questions and hypotheses

| | Research question | Hypothesis |
| --- | --- | --- |
| RQ1 / H1 | Which behavioral features distinguish a human attack from an autonomous-AI APT? | Command telemetry features such as command length, flags, pipes, chaining and redirects improve classification. |
| RQ2 / H2 | Which of gradient boosting, histogram gradient boosting and XGBoost performs best, compared with random forest and logistic regression baselines? | XGBoost achieves the highest macro-F1. |
| RQ3 / H3 | Can XGBoost identify the autonomous AI operator within each tested MITRE ATT&CK stage group? | The operators can be distinguished within each tested stage group. |

## Status and evidence

The draft reports that all three hypotheses are supported **within the study's limits**. It reports held-out-session macro-F1 of 0.857 for XGBoost, 0.840 for gradient boosting, 0.811 for histogram gradient boosting, 0.852 for random forest and 0.806 for logistic regression. XGBoost and random forest were not statistically distinguishable. XGBoost's reported stage-group macro-F1 is 0.777 for discovery, 0.924 for execution and 0.903 for lateral movement/collection; account manipulation had too few AI windows to test. These are paper-reported results, not results produced by the legacy pipeline in this worktree.

**Analysis history:** The imported [original hypotheses and outcomes](study/results_h1_h3/tables/T_original_hypotheses.csv) report H1 and H3 not supported and H2 supported under the definitions fixed before scoring. The imported [analysis record](study/results_h1_h3/RULES_AS_DECIDED.md) states that H1 and H3 were restated after scoring; its numbering differs from the v1.6 paper's RQ/H mapping. Do not treat the later wording as a preregistered confirmation.

The paper reports 951 retained 30-second windows and 60 features across four tiers. The main configuration uses 40 behavior, command-content and associated context features; input-channel features are reported separately because they can reveal the harness. Stages are for splitting and reporting, not classifier inputs. The paper describes leave-one-session-out evaluation and class/session-weighted training.

| Component | Current state |
| --- | --- |
| Paper | User-provided v1.6 draft reviewed; submission, institutional approval and underlying evidence have not been verified here. |
| Collection | [Initial restricted collector](collector/README.md) supports selected CloudWatch log groups and normalized local JSONL across all lab-source categories. Real lab configuration and end-to-end live export remain unverified. |
| Paper-specific research artifacts | [Study code, prompts, reports and available results](study/README.md) imported from `paganpraxis/Human-vs.-Autonomous-AI-Operator-Classification` at commit `43abf244662056a5725864dd3baa05052a5360da`. The 14 code files listed in Freeze 2 match their recorded SHA-256 hashes. |
| Data and model reproduction | The supplied Study 3 archive contains restricted evaluation inputs and saved predictions absent from the source repository. All 51 Freeze 2 entries matched in a private evaluation copy, and the scored-input gate passed. Recalculating macro-F1 from 951 saved XGBoost predictions yields 0.857; no model was refit. The older [synthetic engineering harness](pipeline/README.md) uses a different schema and RQ design. |
| Next | Recreate the pinned Python environment and rerun the paper-specific evaluation in a separate private working copy, preserving the original evidence and saved outputs. Collection and preprocessing replay are outside the current evaluation-only scope. |

The collector intentionally retains restricted raw logs and is not the paper's full exporter or Appendix E verifier. Read its security and verification boundaries before use. Do not commit raw recordings, credentials, operator identities or restricted paths.

The archive also contains a v1.11 paper draft. Its contents and approval status have not been established, so v1.6 remains the reference used here. Archive data, prompts, reports and environment materials require privacy and credential review before any publication.

## Historical October 2026 workspace

The material below documents the earlier proposed design and is retained for provenance. Its prospective RQs, hypotheses, dates and status are **superseded by the paper-aligned summary above**; the older pipeline remains an exploratory engineering artifact.

---

**Identifying Autonomous AI APT** · Owner: Gary Pagan · Created October 19, 2026

**Status: synthetic engineering run completed; scientific protocol not frozen; real collection/training pending.** [RQs/Hs](../../PRAXIS_RESEARCH_DESIGN.md) · [Methodology](../../PRAXIS_EXPERIMENT_PROTOCOL.md) · [Schedule](../../PRAXIS_STATUS_TRACKER.md).

**Runnable engineering harness:** [run RQ1–RQ3 on a synthetic fixture or import a validated feature CSV](pipeline/README.md). This implementation tests the analysis paths; it does not establish the hypotheses or replace the scientific freeze gates.

[Completed synthetic run](pipeline/synthetic_smoke_20261019_v2/REPORT.md) · [Validation record](pipeline/VALIDATION.md) · [CSV import template](pipeline/import_template.csv)

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
| H2 logistic-regression baseline contrast, reference split and attribute-stability summary; any additional transfer-loss criterion | Analysis / Advisor | Oct 26 | Unresolved |
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
