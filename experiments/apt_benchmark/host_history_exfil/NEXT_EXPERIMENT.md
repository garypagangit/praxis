# Next experiment: preserve movement evidence while using host context

**Status: proposed after the completed development results; no new model result claimed.**

## What the new evidence supports

Host roles and correctly linked earlier activity improve exfiltration ranking on later UNRAVELED traffic. A global four-class decision misses every exfiltration label in a new destination-role context. Lowering the exfiltration threshold recovers more cases but also calls many movement rows exfiltration. The next step should isolate these decision and ground-truth issues; merely adding another model is not sufficient evidence of improvement.

## Test A — Separate movement and exfiltration decisions

Use two independently scored outputs: evidence of movement and evidence of exfiltration. Allow both or neither instead of forcing one stage to win. Compare the current-flow movement detector, context exfiltration detector, their simple union, and a learned combination using the same data and features. Keep each individual detector visible as an ablation. Training of any learned combination must be out-of-fold or use a genuinely separate fitting partition.

Compare global exfiltration thresholds with role-conditioned thresholds and an explicit unfamiliar-role indication. Define the role grouping and minimum calibration support before results. A role with no relevant attack calibration examples must be marked unsupported, not assigned a performance guarantee. Normal-only calibration does not constrain movement-to-exfiltration confusion.

Report actual movement recognition, exfiltration recognition, ambiguous/both labels, normal false alerts, other-stage mislabels, and resulting review workload. A protected union can preserve baseline movement flags by construction while increasing alert burden; measure that burden rather than calling the construction a novel detection result. A row with two labels has not been correctly resolved merely because one is true.

The current dataset has **zero movement calibration examples**. A new comparison cannot claim controlled movement error there. Qualify a development partition or additional executions with both behaviors, freeze the revised split before results, and retain all earlier evidence as already exposed development. Do not choose a new threshold on the current evaluation labels and call it confirmation.

## Test B — Verify behavior and vary host roles independently

The literal research question needs ground truth beyond stage tags. Qualify existing host/network evidence or create controlled isolated executions using dummy documents:

- Confirm movement with a successful remote action on a second host, linked to source/destination identities and trustworthy timestamps.
- Confirm exfiltration with receipt of a marked dummy document at the defined unauthorized destination; distinguish attempted, failed, staged and completed transfers.
- Include normal remote administration, internal copies, backups and authorized external uploads. An external connection alone cannot define exfiltration.
- Vary workstation/server roles, internal relay use, protocols and transfer size separately from the labels. Repeat with different host assignments and execution order. Do not put movement or theft at fixed elapsed minutes.
- Hold complete executions and host assignments apart for evaluation. Audit the ground truth separately from predictor construction. A generator manifest or label-derived feature must never become a predictor.
- Build predictors only from information available at the decision time. File reads, archive creation and authentication outcomes can add evidence, but their timestamp and process/host linkage must be qualified first.

This would test whether context adds reusable information when the endpoint role changes. It is an independently specified follow-up; the current 35 movement rows and one campaign cannot supply repeated-execution proof. Locally available UNRAVELED host logs offer a concrete qualification route before building a new corpus; see [host-log feasibility](HOST_LOG_FEASIBILITY.md).

## Literature position

Context models, temporal features and ensembles already exist. The potential applied contribution is a controlled evaluation of **behavior recognition under changed host roles, while retaining movement evidence and counting ambiguous decisions**. Positive current ranking results motivate this question; they do not establish algorithmic novelty. See [primary-source review](DATASET_LITERATURE.md) and the earlier [exfiltration ensemble literature](../exfil_stage_experiments/LITERATURE.md).
