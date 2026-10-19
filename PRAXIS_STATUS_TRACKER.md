# Identifying Autonomous AI APT: project status tracker

**Owner:** Gary Pagan · **Updated:** October 19, 2026 · **Delivery window:** October 19–December 1, 2026 (America/New_York)

**Overall delivery health: AT RISK.** The schedule is compressed and current collection readiness has not been verified. The advisor deck proposes 12–24 pilot trials and places expanded generalization work in January–February 2027. This delivery plan supersedes that schedule: required work, including generalization evaluation, must finish by December 1, 2026. Do not silently defer required RQs beyond the defense.

[Working research questions and hypotheses](PRAXIS_RESEARCH_DESIGN.md) · [Experiment delivery protocol](PRAXIS_EXPERIMENT_PROTOCOL.md) · [Original advisor deck](Final%20Defense%20Idea%20Advisor%20Submission%20V001%2010162026.pptx)

## Fixed milestones and proposed internal gates

Dates for AI Review and defense are user-confirmed. Other dates below are proposed internal targets, not institutional requirements. AI Review package contents and committee circulation rules still require confirmation.

| Gate | Due | Required evidence | Status |
| --- | --- | --- | --- |
| Scope and feasibility decision | Oct 21 | Three RQs, hypotheses, recruitment commitments, sample/precision plan, compute budget and achievable collection schedule | Open |
| Gate A: collection readiness | Oct 23 | Reset attestation, sensor canaries, clock/loss checks, matched access and autonomy demonstration | Unverified |
| Pilot and protocol freeze | Oct 26 | Pilot audit, final independent-trial counts, preregistered splits/features/metrics and tuning limits | Planned |
| Matched collection complete | Nov 2 | Human, AI, held-out operators/configurations and control trial manifests | Planned |
| Dataset and feature freeze | Nov 3 | Validated immutable data, exclusions, feature schema and disjoint split manifest | Planned |
| Model selection and locked evaluation | Nov 7 | Frozen candidates, RQ1–RQ3 outputs, uncertainty and failure analysis | Planned |
| Complete Praxis draft and reproducibility audit | Nov 10 | Draft chapters, traceable tables, replay check and limitations | Planned |
| AI Review package ready | Nov 12 | Required contents confirmed, author review and versioned package | Planned |
| **AI Review (AIR) submission** | **Nov 14** | Submitted package and receipt | Planned — fixed deadline |
| Review revisions and committee package | Nov 20 | Response matrix and committee-ready manuscript; verify actual circulation deadline by Oct 20 | Planned |
| Defense slide freeze | Nov 24 | Slides, backup evidence and complete RQ-to-result traceability | Planned |
| Mock defense | Nov 27 | Timed rehearsal, question log and corrections | Planned |
| Final readiness check | Nov 30 | Manuscript/slides accessible, logistics tested, final rehearsal | Planned |
| **Defense and delivery handoff** | **Dec 1** | Delivered defense, outcome/feedback record and archived package | Planned — fixed date |

## Status rules

**Done:** linked, checked deliverable. **Draft:** content exists but is not approved/frozen. **Reported in progress:** the October 16 deck says work is underway; current completion is unverified. **Planned:** scheduled, with no completion evidence inspected. **Blocked:** named dependency prevents progress. No research completion percentage is asserted from planning documents.

Gary owns delivery and status updates. Roles below are proposed assignments until a named person accepts them: **Lab** = lab/evidence lead; **Human** = human red-team lead; **AI** = AI operator lead; **Analysis** = analyst; **Advisor** = academic reviewer. Gary remains accountable where a role is unfilled.

## Work breakdown and acceptance checks

Every row is due inside October 19–December 1, 2026. Dependencies are completion requirements; preparation may overlap. Evidence marked “pending” must be replaced with a commit/file link or restricted evidence-manifest reference before marking Done.

| ID | Work item / deliverable | Owner | Start → due | Depends on | Status / evidence | Completion check |
| --- | --- | --- | --- | --- | --- | --- |
| P01 | Project tracker and delivery plan | Gary | Oct 19 → Oct 19 | — | Done — this file | Fixed dates, owners, dependencies and risks recorded |
| P02 | Problem statement | Gary | Oct 19 → Oct 21 | — | Draft — deck slide 2; revised framing in research design | Bounded target-side attribution gap; verify every prevalence/cost claim |
| P03 | Thesis and contribution | Gary | Oct 19 → Oct 21 | P02 | Draft — deck slide 3; research design | Testable thesis; contribution distinguished from existing work |
| P04 | RQ1–RQ3 revision | Gary / Advisor | Oct 19 → Oct 21 | P02,P03 | Draft — research design | Features, transfer and classifier comparison separated; advisor review recorded |
| P05 | H1–H3 and decision rules | Analysis / Advisor | Oct 19 → Oct 22 | P04 | Draft — research design | Nulls, metrics, margins, uncertainty and multiplicity frozen |
| P06 | Literature and novelty matrix | Gary | Oct 19 → Oct 22 | P02 | Draft — research design sources | Human vs AI, AI-family fingerprinting and tabular benchmarks compared; unsupported “first” claims removed |
| P07 | AI Review and defense requirements | Gary | Oct 19 → Oct 20 | — | Planned — pending | AI Review checklist, recipient, submission method/time, committee notice/circulation and formatting confirmed |
| P08 | Scope, sample size and resource feasibility | Gary / Analysis | Oct 19 → Oct 21 | P04 | Planned — pending | Independent trials/operators/configurations, uncertainty target, availability and budget support all RQs |
| D01 | Red-team plan and rules of engagement | Human / Lab | Oct 19 → Oct 22 | P08 | Reported in progress — deck slide 21 | Matched objective, access window, stop rules, allowed lab scope, reset and counterbalancing fixed |
| D02 | Human red-team preparation | Human | Oct 19 → Oct 23 | D01 | Planned — deck slide 22 | Recruit operators, record experience/exposure, consent and required institutional determination before collection |
| D03 | Lab and host telemetry | Lab | Oct 19 → Oct 23 | D01 | Reported in progress — deck slide 19 | Pinned lab revision and image IDs; target-side host sources verified |
| D04 | Network sensor and evidence archive | Lab | Oct 19 → Oct 23 | D01 | Reported in progress — deck slide 19 | Sensor coverage, native exports, restricted archive and checksum manifests verified |
| D05 | AI red-team preparation | AI | Oct 19 → Oct 23 | D01,P08 | Planned — deck slide 22 | Model/scaffold/prompt/runtime pinned, autonomy shown, latency measured, held-out family/config reserved |
| D06 | Gate A: data collection validation | Lab | Oct 22 → Oct 23 | D03,D04,D05 | Planned — deck slide 20 | Canary coverage, reset attestation, UTC offsets and loss checks pass; documented remediation for failures |
| D07 | Human red-team initiation / pilot | Human | Oct 24 → Oct 25 | D02,D06 | Planned — pending | First matched pilot trials archived, intervention/outcome logs complete |
| D08 | AI red-team initiation / pilot | AI | Oct 24 → Oct 25 | D05,D06 | Planned — pending | Autonomous pilot trials archived under same interface and constraints |
| D09 | Pilot evaluation and protocol freeze | Analysis | Oct 25 → Oct 26 | D07,D08,P05 | Planned — pending | Feasibility, learning-curve plan, trial budgets, splits and exclusions frozen; exposed pilots tagged development |
| D10 | Human scored collection | Human | Oct 27 → Nov 2 | D09 | Planned — pending | Planned human trial cells including held-out operators complete; no silent exclusions |
| D11 | AI scored collection | AI | Oct 27 → Nov 2 | D09 | Planned — pending | Planned AI trial cells including reserved configurations complete; failed/aborted runs retained in registry |
| D12 | Benign and scripted controls | Lab | Oct 27 → Nov 2 | D09 | Planned — pending | Benign and scripted replay labels separate from human/AI; matched telemetry captured |
| D13 | Data validation and collection close | Lab / Analysis | Oct 27 → Nov 3 | D10,D11,D12 | Planned — pending | Hashes, labels, joins, duplicates, missingness, clock offsets and exclusions independently checked |
| M01 | Methodology and preregistration | Analysis | Oct 19 → Oct 26 | P05,P08,D07,D08 | Draft — experiment protocol | Full protocol and analysis plan versioned before scored collection |
| M02 | Data evaluation / descriptive audit | Analysis | Oct 24 → Nov 3 | D13 | Planned — pending | Trial/group/class counts, coverage and missingness tables; no test-driven design changes |
| M03 | Feature engineering and dictionary | Analysis | Oct 22 → Nov 3 | M01,D13 | Planned — deck slide 25 | Host/network families, aggregation, rates and deny-list implemented; training-only fitted transforms |
| M04 | Model identification and compute gate | Analysis | Oct 22 → Oct 26 | P08,M01 | Draft — research design | XGBoost, decision tree, random forest, SVM, FT-Transformer and baselines specified; resources and capacity checked |
| M05 | Experiment harness and smoke checks | Analysis | Oct 24 → Nov 3 | M04,M01 | Planned — pending | Reusable folds, bounded search, logging, seeds and trial roll-up tested on development data |
| M06 | Model training and tuning | Analysis | Nov 4 → Nov 5 | M02,M03,M04,M05 | Planned — pending | Identical grouped splits, fair search caps and complete run manifests; no locked-test access |
| E01 | RQ1: feature identification experiments | Analysis | Nov 4 → Nov 6 | M06 | Planned — pending | Grouped family permutation/ablation on development folds; stable feature report |
| E02 | RQ2: transfer and shortcut experiments | Analysis | Nov 4 → Nov 6 | M06 | Planned — pending | Development operator/config holdouts, ranking stability, timing/tool ablations and transfer gaps |
| E03 | RQ3: model comparison and selection freeze | Analysis | Nov 6 → Nov 6 | E01,E02 | Planned — pending | Selection rule applied to development results; all finalists frozen |
| E04 | Locked evaluation of all frozen candidates | Analysis | Nov 7 → Nov 7 | E03 | Planned — pending | One batch evaluation; per-trial predictions, paired uncertainty and baseline contrasts stored |
| E05 | Results evaluation and error analysis | Analysis | Nov 7 → Nov 9 | E04 | Planned — pending | RQ/H disposition, confusion matrices, false AI labels on humans, benign control outcomes and limitations |
| E06 | Reproducibility and independent audit | Lab / Analysis | Nov 8 → Nov 10 | E05 | Planned — pending | Raw evidence → features → predictions → tables replay; checksums and environment captured |
| W01 | Praxis development: introduction / literature | Gary | Oct 19 → Oct 28 | P02,P03,P06 | Draft — advisor deck is source material | Chapters linked to citations and bounded contribution |
| W02 | Praxis development: methods | Gary | Oct 24 → Nov 4 | M01,D13 | Planned — pending | Actual collection, protocol deviations and evaluation design described |
| W03 | Praxis development: results | Gary | Nov 7 → Nov 10 | E05 | Planned — pending | Every table tied to prediction artifact and trial denominator |
| W04 | Conclusion, limitations and contribution | Gary | Nov 9 → Nov 10 | E05 | Planned — pending | Answer each RQ, evaluate each H, delimit APT claims and unsupported generalization |
| W05 | Full draft / advisor review / corrections | Gary / Advisor | Nov 10 → Nov 12 | W01,W02,W03,W04,E06 | Planned — pending | Complete manuscript, bibliography, figures and review-response log |
| A01 | AI Review package preparation | Gary | Nov 10 → Nov 12 | P07,W05 | Planned — pending | Confirmed required files, attribution/disclosures if required, version and author check complete |
| A02 | AI Review submission | Gary | Nov 13 → Nov 14 | A01 | Planned — fixed deadline | Submit to confirmed destination and record receipt |
| A03 | AI Review corrections / committee package | Gary | Nov 15 → Nov 20 | A02 | Planned — pending | Address returned feedback; if delayed, escalate and record pending feedback explicitly |
| F01 | Defense slides | Gary | Nov 15 → Nov 24 | W05,E06 | Planned — pending | Problem, thesis, RQs/Hs, methods, results, limitations and contribution; backup statistics |
| F02 | Defense logistics and committee confirmation | Gary | Oct 19 → Nov 20 | P07 | Planned — pending | Dec 1 time/location/link, members, circulation cutoff and equipment confirmed |
| F03 | Mock defense and question bank | Gary / Advisor | Nov 25 → Nov 27 | F01,A03 | Planned — pending | Timed rehearsal and responses on leakage, sample size, novelty, model choice and negative outcomes |
| F04 | Final revisions and package freeze | Gary | Nov 28 → Nov 30 | F03,F02 | Planned — pending | Final manuscript, slides, backup PDF and reproducibility package versioned and accessible |
| F05 | Defense and outcome record | Gary | Dec 1 → Dec 1 | F04 | Planned — fixed date | Deliver defense, record committee outcome and any requested corrections |
| F06 | Final delivery archive and handoff | Gary | Dec 1 → Dec 1 | F05 | Planned — pending | Archive delivered versions and correction register; confirm institutional deposit/signoff requirements with P07 |

## Critical path and weekly delivery

**Scope/resources → lab readiness → matched pilots → protocol freeze → collection → validated data → trained/frozen models → locked evaluation → full draft → AI Review → revisions → defense.** Human recruitment and AI configuration availability run in parallel with the lab and can block this path. Writing begins immediately.

| Week | Required outcome |
| --- | --- |
| Oct 19–25 | Scope and staffing commitments, advisor RQ review, Gate A and pilots |
| Oct 26–Nov 1 | Freeze protocol, run matched collection, draft methods and feature pipeline |
| Nov 2–8 | Close and validate data, train, ablate, freeze candidates and evaluate |
| Nov 9–15 | Complete manuscript and audit; submit AI Review by Nov 14 |
| Nov 16–22 | Review responses, committee-ready package, defense draft and logistics |
| Nov 23–29 | Freeze slides, rehearse, repair weak explanations |
| Nov 30–Dec 1 | Final check, defense and delivery archive |

## Risks, decisions and recovery actions

| Risk / decision | Owner / decision date | Response and escalation |
| --- | --- | --- |
| RQ2 needs unseen groups; a single AI family cannot establish family transfer | Gary / Oct 21 | Confirm distinct human operators and AI model families/configurations before collection; narrow the claim explicitly if unavailable |
| 12–24 independent pilot trials may not support reliable model ranking | Analysis / Oct 21, recheck Oct 26 | Use variance/precision analysis and pilot learning curves; windows do not increase independent trial count. Escalate inadequate support rather than promise a winner |
| Original January–February 2027 phase conflicts with Dec 1 defense | Gary / Oct 21 | Move required transfer collection into Oct 27–Nov 2; reserve future work only for extensions outside the three required RQs |
| Gate A slips beyond Oct 23 or dataset freeze beyond Nov 3 | Gary / at missed gate | Rebaseline staffing/compute and scope with advisor immediately; keep Nov 14 and Dec 1 visible; no shortcuts in data integrity or hidden test reuse |
| Transformer lacks data, time or resources | Analysis / Oct 26 | Preserve its planned comparison; document a feasibility failure if necessary. Do not present an unrun model as evaluated or add extra data representations without labeling them |
| AI Review contents, feedback turnaround and committee deadline unknown | Gary / Oct 20 | Obtain official checklist and lead times; internal Nov 20 target must move earlier if circulation rules require it |
| Only one scenario or constrained lab | Gary / Nov 10 | Report controlled APT-like lab attribution; do not generalize to all real-world APT campaigns |
| New findings after Nov 14 | Gary / as needed | Version corrections and submit/distribute under confirmed program rules; never silently replace reviewed results |
| Post-defense corrections requested | Gary / Dec 1 | Record them at defense. All planned work ends Dec 1; any externally imposed later requirement needs an explicit revised deadline |

## Maintenance and evidence log

Update rows whenever evidence or dates change; review critical dependencies each Monday and Thursday through defense. For every Done row, record the artifact path/commit, completion date and reviewer. Record blockers with an owner, next action and recovery date. Do not put raw telemetry, credentials, human identities or restricted participant records in the public tracker.

| Date | Change / evidence | Next action |
| --- | --- | --- |
| Oct 19 | Advisor deck published at root in commit `cdafed6`; original bytes preserved | Align working research plan with new delivery dates |
| Oct 19 | Tracker, revised working RQs and experiment protocol created | Confirm owners, AI Review checklist and Oct 21 feasibility decision |
