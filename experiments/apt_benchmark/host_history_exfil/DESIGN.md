# Host roles and earlier activity: alternative-dataset test

September 22, 2026. New development experiment, preserving all earlier SCVIC studies.

## Research question and measured proxy

**Question:** Can host roles and earlier activity help distinguish movement through a network from data being stolen?

The available UNRAVELED data can test a narrower proxy: whether those observations improve classification of the **author's Lateral Movement and Data Exfiltration stage annotations** on later captured traffic. It cannot independently prove successful host movement or theft. All IT-sensor movement annotations have Activity=`Remote System Discovery` on one directed host pair; the author Stage describes campaign progress. Some exfiltration annotations elsewhere have Activity=`Unsecured Credentials`. Preserve these labels and disclose their meaning; do not relabel them based on desired results.

## Why this dataset

[UNRAVELED](https://doi.org/10.1016/j.comnet.2023.109688) has identities, time order, static network topology, normal activity, and substantially more labeled exfiltration than the acquired DEDALE subset. Its files were already used in earlier GML work, so this is alternative-dataset development, not an untouched holdout. The study contains one emulated APT campaign alongside less-skilled attacks, not 31 independent campaigns.

The [input qualification](PILOT_INPUTS.json) locks eleven complete `net1013x` sensor files. Using one sensor removes the easy shortcut of recognizing which interface supplied a row. It does not remove fixed-host or stage-label confounding. Do not pool mirrored interfaces as independent observations.

## Fixed temporal split

Use the five Week5 Day1 through Day5-6 files for fitting, the next Week5 Day6 file for calibration, and the five Week6 IT-sensor files for evaluation. Use actual first/last packet times, not the potentially misleading directory dates. Assert that the fitting period ends before calibration starts and calibration ends before evaluation starts. No random row partitioning.

| Author labels before any cross-file deduplication | Fit | Calibration | Evaluation |
|---|---:|---:|---:|
| Benign | 147,087 | 8,929 | 192,193 |
| Lateral Movement | 27 | 0 | 35 |
| Data Exfiltration | 1,740 | 1,331 | 3,442 |
| Other attack stages | 12,362 | 2,659 | 12,424 |

The shared **department-to-private-services** evaluation stratum has 35 movement and 1,101 exfiltration rows. Its fitting partition has 27 movement and **zero exfiltration** examples. This is a meaningful destination-context shift, not a balanced same-role training test. Calibration has no movement cases, so movement thresholds or calibration coverage cannot be learned or certified there. Report actual counts and uncertainty in interpretation.

## Parser and observation integrity

The author CSVs contain unquoted commas in DPI strings. Ordinary positional reading shifts annotation columns on some rows. The qualified reader uses the intact numeric/identity prefix, columns 0–76, and validates annotations anchored at the right-hand end. It excludes the entire malformed DPI region. Stop on unresolved annotations, schema changes, or nonfinite numeric prefix values. This recovers existing author labels; it is not an inferred correction of attack truth.

Hash every source against the pinned author-byte audit. Deduplicate identical observable event identities across these files and quarantine conflicting labels; document any changes. Keep source-file/row linkage private. No label, Activity, Signature, DefenderResponse, literal IP/MAC, capture identifier or absolute clock value is a model predictor.

## Six matched arms

All use the same fixed LightGBM configuration and fitting identities:

1. Current completed-flow features only.
2. Current features plus coarse host roles.
3. Current features plus earlier activity.
4. Current features plus roles and earlier activity.
5. Current features plus roles and an intentionally **wrong host's earlier activity**, as a history-linkage control.
6. Roles alone, as a diagnostic of topology shortcuts.

Roles come from the author's static topology: department subnets, public-service subnet, private-service subnet, and other address. “Other address” does not establish a hostile or Internet destination. Do not feed individual department IDs or known compromised-host identities to the model.

For each source and destination, summarize the preceding 5 and 30 minutes: completed flow counts, transmitted/received bytes, distinct peers, initiated flows, remote-administration service counts, internal-peer counts, prior contact with the current peer, and whether the host has been seen. Remote-service categories are ordinary port observations, not claims that those connections are malicious. Current-flow service categories are available equally to all current-feature arms.

Only flows whose last observed packet precedes the current flow's **first** packet enter history. Equal timestamps and overlapping uncompleted flows are excluded. Compute histories over all qualified traffic before fitting-row subsampling. No ground-truth stage or model prediction contributes to history. Continue label-free state through fitting, calibration and evaluation: this is observable traffic history, not target-label adaptation. A flow-completion/export delay is unmeasured; the decision itself uses full-flow features and is not an early-warning result.

The wrong-host control picks a different host deterministically from the inventory observed so far and queries its state at the same time. It never imports future history. This control changes only history correspondence; current roles remain correct. It is a diagnostic, not a deployment method.

## Fitting and evaluation

Three fitting seeds, with at most 20,000 benign and 5,000 rows per other class, sampled from fitting captures by stable hashes. Every arm within a seed uses identical rows. Each fixed LightGBM has 300 trees, 15 leaves, learning rate .05, minimum child count 10, L2=1, four CPU threads, no class weighting or parameter search. All calibration/evaluation rows remain in their natural proportions.

Publish all six arms, each fitting seed, each later capture and each role-pair stratum. Report exfiltration AP, F1/precision/recall, false exfiltration labels from each true class, four-class confusion/macro-F1, and movement exact-stage and any-attack recall. For the exfiltration-versus-movement challenge, publish AP together with its very high exfiltration prevalence; high AP alone can be misleading when movement is sparse. Missing classes receive N/A for ranking metrics, never invented perfect performance.

Choose exfiltration F1 thresholds only on calibration rows. Also report nominal 0.1%, 0.5%, 1% and 2% non-exfiltration calibration tails and observed later error counts. These percentages are descriptive operating points, not acceptance standards or population guarantees. The source has no calibration movement cases, a specific limitation of these thresholds.

The informative contrasts are roles versus current, history versus current, both versus each component, and both versus wrong-host history. Gains confined to role-identifiable rows do not establish that history distinguishes same-role attacks. No arbitrary 90% pass/fail requirement, post-result threshold changes, or fitting-seed population confidence interval.

## What would answer the original question more strongly

Even a positive author-stage result needs event-verified evidence in independent executions. A follow-up can use multiple controlled, isolated network scenarios with dummy documents and known transaction outcomes: verified remote action on another host versus verified transfer of a marked dummy file, plus benign administration and backups. Vary roles and traffic volumes independently; keep campaign/host assignments disjoint between fitting and evaluation, and hide the manifest from predictors. The [dataset review](DATASET_LITERATURE.md) and new-source probe explain why nominal stage labels alone are insufficient.

That independently labeled follow-up is a separate experiment, not a result generated or promised by this pilot.
