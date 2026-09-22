# Validity review: host roles and earlier activity for stage identification

Review date: September 22, 2026. Scope: independent design and source inspection; no model fitting or outcome-based choice of a new method. UNRAVELED can support a new chronological, capture-grouped **development** experiment. Its available bytes were used in earlier GML research, and its sustained APT is not a collection of independent campaigns.

## 1. What is available, and what was already used

The [qualification receipt](../tabular_followup/UNRAVELED_QUALIFICATION.json) binds 173 author CSVs in 31 named capture directories to author commit `d2ea90055d82fa448ab20588a13e3ec8bfd74816`. It counts 6,877,157 raw rows, including 27,445 `Lateral Movement` and 7,522 `Data Exfiltration` rows. All 173 files were represented in the previous GML cache. These are raw observation counts before capture-overlap, duplicate-flow, and label-conflict handling.

The locally available pinned author [repository README](https://gitlab.com/asu22/unraveled/-/blob/d2ea90055d82fa448ab20588a13e3ec8bfd74816/README.md), [data README](https://gitlab.com/asu22/unraveled/-/blob/d2ea90055d82fa448ab20588a13e3ec8bfd74816/data/README.md), and [network diagram](https://gitlab.com/asu22/unraveled/-/blob/d2ea90055d82fa448ab20588a13e3ec8bfd74816/images/system-model.png) were inspected directly from the local author checkout for this review. The dataset paper is Myneni et al. (2023), [*Unraveled: A semi-synthetic dataset for Advanced Persistent Threats*](https://doi.org/10.1016/j.comnet.2023.109688). No new literature-performance claim is inferred from the dataset's availability.

The old [GML loader](../../../src/praxis/unraveled_v02.py) retained selected attack stages, optionally subsampled benign rows, sorted flows by **first** packet time, and added sensor/gateway indicators. Its prepared cache is unsuitable as the complete input for the proposed history features: removed background changes counts and destination novelty, and first-packet sorting does not make completed-flow statistics available at flow start. The [earlier correction](../../apt_final/docs/LITERATURE_CORRECTION_20260920.md) also records that the 435,488-row v03 cache had empty Signature values and no verified independent-campaign identifiers. Reconstruct this experiment from qualified raw flow tables, not that cache.

The [experiment inventory](../../../EXPERIMENTS.md) documents poor earlier Exfiltration classification, including zero Exfiltration F1 for the listed GML comparisons. That motivates examining new information; it neither proves that graph learning cannot work nor supplies a matched baseline for the new split and context features.

## 2. Capture overlap is a material design issue

The author explicitly states that subnet-to-Internet traffic is observed at both a subnet interface (`net1011x` through `net1015x`) and `netgw`. Intra-subnet traffic is not observed by these gateway capture points. Therefore:

- A CSV is an observation view, not an independent attack or capture episode.
- Different sensors from the same acquisition interval must stay in the same evaluation block.
- Combining sensors without deduplication inflates history counts, byte totals, and apparent event support.
- A missing intra-subnet event is missing visibility; it must not become a negative label or a claim that lateral activity did not occur.

Directory names also overlap or have ambiguous dates: `Week4_Day03_06162021` versus `Week4_Day3_7_06162021_06202021`; two Week4 directories contain `06152021`; July 2 has part1 and part2. Use measured first/last timestamps and capture provenance, not lexical directory order or filename dates alone. Build connected acquisition blocks from overlapping intervals and known mirror sensors. Keep any ambiguous overlap together or quarantine it before choosing train/calibration/test boundaries.

The prior raw audit shows a strong stage/sensor association. For June 25–26, `net1013x` has 1,299 Exfiltration and nine Lateral rows, whereas the corresponding `netgw` has one Exfiltration and 5,764 Lateral rows. July 3–4 contains 694 Exfiltration rows in both `net1013x` and `net1015x`. Equal counts are a reason to check mirrored flows, not proof that the rows are duplicates. This association may reflect actual collection paths, annotation scope, or both; it is not by itself proof of incorrect labeling.

**Minimal defensible sensor policy:** freeze an observation rule before outcomes. Either use one clearly named sensor with enough stage support and state its limited field of view, or merge qualified internal sensors with a deterministic canonical flow-observation rule. Excluding `netgw` alone does not resolve mirrored inter-subnet traffic. A reverse-direction-aware endpoint/port/protocol/time key can identify candidate duplicates, but timing differences, flow expiration, and NAT require qualification. Do not merge arbitrary similar vectors or assume a tolerance without checking it. Resolve conflicting Stage values by documented author evidence; otherwise quarantine the group. Publish raw, canonical, conflict, excluded, and per-sensor retained counts.

## 3. Labels describe author stages, not necessarily individual actions

The raw stage/signature audit has all 7,522 Exfiltration and 27,445 Lateral rows tagged `APT`. Signature denotes attacker category, not an independent campaign identifier. The README describes one sustained APT alongside less-skilled scenarios.

The author defines Stage as attacker progress. Its Exfiltration narrative includes channel establishment, credential retrieval, database access, data staging, and transfer. Thus the task should be described as **classification of author-labeled stage-associated flows**, unless independent event evidence establishes a narrower action label. It cannot automatically be called proof that every Exfiltration-labeled flow contains stolen data, that each Lateral-labeled row moves to a new host, or that an incident was detected early.

Keep `Stage`, `Activity`, `DefenderResponse`, and `Signature` out of model inputs, histories, role definitions, and context-donor selection. Quarantine the 1,493 rows with unresolved numeric Stage strings (`6`, `7`, `26`, `33`); do not invent a mapping. `Benign` and `Normal` are observed source values whose merge must be explicitly qualified and recorded. Other valid attack stages must remain in an `OtherAttack` class or a declared full stage taxonomy, rather than disappearing from an apparently successful Exfiltration-versus-Lateral evaluation. A three-way classification on only benign/LM/Exfil is valid only with that filtered scope explicit and a competing-stage diagnostic retained.

The author's broad statement that week 1 was normal-only conflicts with the raw audit's 28 LM/APT rows in the first directory. Do not silently certify that entire week as clean. A label-blind warm-up using earlier observed traffic remains possible; label it as unlabeled historical activity unless the discrepancy is resolved. Choosing only rows retrospectively labeled benign to estimate a role at deployment time is privileged information unless such clean-history availability is a separately declared assumption.

## 4. Host roles available without attack hindsight

The inspected author diagram gives legitimate coarse network roles:

| Static network location | Qualified coarse role |
|---|---|
| `10.1.1.0/24`, `10.1.2.0/24`, `10.1.3.0/24` | Corporate user networks |
| `10.1.4.0/24` | Public-service subnet, containing web/honeypot services |
| `10.1.5.0/24` | Private production services, including application/database/log/SFTP systems |
| Address outside qualified inventory | External/unknown, with parsing failures separate |

Prefer these coarse roles to department IDs for the primary pilot. The IT subnet is strongly associated with the known attack story, so its literal subnet identifier could function as a site-specific proxy. The diagram does not identify each individual server's exact IP. Do not infer a database-server IP, attacker IP, victim IP, or DBA identity from target labels or the attack narrative and then claim the feature was independently available inventory.

Use source/destination role, same-versus-cross network role, corporate-to-production, and internal-to-external relations. Orient current-flow bytes to a declared inventory role when the endpoint relation is unambiguous. For example, corporate-to-external byte direction is observable; calling it *victim exfiltration* requires unavailable security truth. Preserve an ambiguous/unknown category instead of resolving it from the label.

An optional behavioral role must be learned from pre-cutoff activity without labels: incoming-service fraction, peer diversity, or coarse port-family usage, with the rule and fitting window fixed. Refit role models only on training/warm-up history, or update them causally without evaluation labels under an explicitly online protocol. `ipaddress.is_private` is insufficient to distinguish the author's public-service subnet from corporate or production roles because all use private addresses.

Exclude literal IP/MAC/OUI, exact host ID, sensor ID, source filename, directory/date, absolute timestamp, and label-derived identities from predictive columns. They may be retained privately as grouping and state keys. Role improvements need within-role-pair and within-sensor diagnostics; a broad aggregate gain may otherwise mainly recover which capture path was assigned a stage.

## 5. Define the observation time before constructing history

For this flow-table pilot, define a decision at the current flow's completion, using `bidirectional_last_seen_ms` as the declared proxy for record availability. NFStream may export after that time; absent export timestamps, actual online delivery latency remains unmeasured. Completed statistics cannot support a flow-start or early-warning claim.

For anchor flow i at time t, only records with valid completion time **strictly less than t** may contribute. Do not use a flow that started earlier but ends later. Exclude the anchor and its duplicate observations. Compute all anchors sharing a completion timestamp before inserting any of that timestamp's records into state. This makes features independent of arbitrary CSV row order and prevents tied flows from seeing each other as past.

Freeze a compact context set, for example a five-minute and one-hour window:

- Number of completed prior flows, packets, and bytes involving each endpoint; separate observed sent/received orientation where reliable.
- Distinct prior peers and service-port families; elapsed time since last completed interaction; whether the current destination is new relative to the observed lookback.
- Prior interactions for the same unordered host pair and directional endpoint pair.
- Prior corporate-to-production and internal-to-external completed-transfer counts/bytes under the static inventory map.

Window lengths are chosen pilot settings, not a discovered optimum. Use event time consistently, evict expired records, and record history exposure/empty-state indicators. A capture gap resets or marks incomplete history; zero observed activity is not proof of no activity. No future-host totals, full-day distinct destinations, capture-wide normalization, retrospectively selected *benign* history, or previous true attack-stage counts are permitted.

Compute history from the complete qualified observation stream **before** any label-based fitting subsample. Dropping background first changes the measurement. Ambiguous-label records may contribute label-free telemetry when their timing and schema are valid, while remaining excluded as supervised anchors; freeze that distinction. Unobserved or malformed timing records cannot contribute precise chronology.

## 6. Chronological, capture-disjoint evaluation

Freeze train, calibration, and final evaluation blocks before fitting. A feasible starting schedule to qualify is earlier captures through June 26 for fitting, June 27–29 for calibration, and June 30–July 4 for final evaluation, because Exfiltration appears in each broad period. These are **proposed boundaries**, not a registered or validated split. Measured acquisition bounds, mirror deduplication, retained class counts, and source visibility must determine whether they are usable. An overlapping multi-day block must not be cut merely to satisfy the proposed calendar split.

All sensors and canonical observations for an acquisition block stay together. There must be no anchor, mirrored observation, duplicate source record, or training label shared across partitions. A long flow crossing a boundary belongs by the declared observation time; an overlap-group rule may require quarantine or assigning its whole acquisition group together. Calendar and capture-disjointness assertions must both pass.

Choose one of these state policies explicitly:

1. **Online continuation:** models and thresholds freeze after training/calibration, but later test anchors can use earlier observed unlabeled traffic, including earlier test records. This is causal online evaluation, not leakage; no test label changes model/state rules.
2. **Capture cold start:** reset history at each independent block and use a declared warm-up whose anchors are excluded from scoring. This is a stronger reset condition with a different information budget.

Report the primary state policy and, if affordable, a prespecified reset diagnostic. Do not present continuation from known training hosts as unseen-host performance. Different time blocks of one sustained APT provide temporal evaluation within the same campaign, not independent-campaign confirmation. Fitting seeds are algorithm repetitions, not extra attacks.

**Bounded implementation option discussed with the parent:** restrict to `net1013x`; train on June 21–26, calibrate on June 27, and evaluate June 29–July 4 after verifying actual capture bounds. Use all qualified traffic for five-minute/30-minute histories before applying a fitting-only cap. This removes cross-interface merging from the first pilot while narrowing visibility. The raw audit reports zero LM rows in the June 27 `net1013x` file and approximately 35 LM rows across the proposed later test files. Therefore LM calibration coverage or a tuned LM operating threshold is unsupported in that calibration period; an absent-class metric must be N/A, not a fabricated zero or one. Test support remains small and must be recounted after qualification. This is a proposed bounded implementation, not a claim that the split has passed its count/overlap gates.

Do not balance or oversample calibration/test anchors. A bounded fit subset is acceptable after history construction, with the same indices for every arm. If full evaluation background is too large, use a frozen label-independent hash sample or a disclosed stratified sample with inclusion weights and separate unweighted sample metrics. Never replace natural prevalence silently.

## 7. Minimal experiment and negative control

Hold the model family, fitting labels, hyperparameters, preprocessing, calibration, and anchor roster fixed:

| Arm | Predictive information |
|---|---|
| B | Identifier-free current completed-flow features |
| B+R | B plus qualified coarse role/direction relations |
| B+H | B plus strictly earlier-flow history |
| B+R+H | B plus both context sources |
| B+shuffled context | B plus a fixed causal wrong-host role/history bundle |

The baseline must include the same current-flow transformations used by context arms, so simple byte scaling is not credited to host history. Keep specialist/fusion changes out of the first pilot; add a specialist only in a separately frozen second stage if context value survives these controls. A fixed boosted-tree configuration is adequate for bounded feasibility, with no claim that it is the best possible model.

**Negative-control construction:** freeze a nonidentity host-donor mapping without labels, using the known inventory or hosts observed by the warm-up cutoff. Maintain history under true observation keys, but retrieve another mapped host's state as it exists at the anchor time for the shuffled arm. Do not rename both observations and lookups together: that preserves the original correspondence and is not a negative control. Do not randomly permute whole-capture feature vectors: that can supply future history. Unknown/unmapped endpoints use declared defaults; report the fraction of anchors actually perturbed. Role/history shuffling should preserve available information and feature dimensions as far as practical, but it is a diagnostic of correspondence, not a formal causal proof.

Train and evaluate every arm under its own declared correct/decoy context rule. An additional evaluation-only corruption diagnostic, if desired, measures dependence of a fitted model on correspondence; it answers a different question and must not replace the trained shuffled control. No shuffle seed is chosen after observing a favorable gap.

If the bounded implementation keeps the true static roles and changes only the history donor, name the arm **wrong-host history with true roles**. It tests whether the correct host-history correspondence matters beyond the role-only baseline; it does not falsify all context information. A donor inventory fixed from training hosts is available for future calibration/test use. Do not derive that inventory from future test hosts; report missing donor/state exposure explicitly.

## 8. Metrics and claims that the data can support

Primary descriptive comparisons: B+R+H versus B, B+R, B+H, and the shuffled arm. Use exact-stage Exfiltration AP/F1 and Lateral AP/F1, plus full confusion, not only any-attack recall. If the target is four classes, explicitly name Normal, Lateral, Exfiltration, and OtherAttack and document the author-label map.

Report:

- Precision, recall, F1, ROC-AUC, and AP for Exfiltration and Lateral; both directions of LM/Exfil confusion; false stage predictions on normal and other attacks.
- Macro-F1 and any-attack metrics separately; raw numerators/denominators and prevalence, per capture block and pooled with weighting stated.
- Calibration-locked threshold operating points and resulting false alerts; no test-selected threshold or universal invented 90% acceptance standard.
- Correct versus shuffled context changes, empty-history cases, role pairs, sensor views, and new/previously observed hosts.
- Time/compute and any extra inventory or label information; no analyst-hours or prevented-incident claim.

A positive pilot would support a narrow finding that legitimately available past/context information improves held-later-capture stage classification in this known environment. It would not establish a new graph algorithm, host attribution, unknown-campaign generalization, actual data-theft semantics, earlier detection, or robustness to missing logs. The setup's single APT story and sensor-stage association constrain novelty and generalization even if all measured gains are large.

## 9. Minimum release and audit checks

Before fitting, retain a source-byte manifest; author-label map and unknown counts; acquisition interval/component roster; canonical observation/duplicate/conflict counts; role-map provenance; feature formulas and availability time; partition boundaries; shared fitting identities; negative-control mapping seed; and arm/metric roster. Do not claim source-independent confirmation merely because the new split differs from earlier GML splits.

Meaningful software tests should establish that changing future rows cannot change any earlier feature, reordering tied-completion rows cannot change features, a long unfinished flow contributes nothing, duplicated observations do not double history, role construction ignores every target-label field, and no overlapping capture group crosses partitions. A chronological replay audit should reconstruct context for sampled anchors from earlier raw records, independently of the training function, and verify that every donor was available at its query time. Recompute metrics from saved predictions and preserve every frozen arm, including negative results.

If capture overlaps, label conflicts, or clock alignment cannot be resolved, report the qualified subset and narrower scope or stop the claimed chronological experiment. Do not repair those gaps by calling directory names independent campaigns, by excluding unfavorable captures after fitting, or by using true victim/attacker labels as host roles.
