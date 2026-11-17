# Expanded defender telemetry experiments

This exploratory follow-on compares window lengths, XGBoost, additional log
channels and timing features, and SMOTE. It does not modify the original Study 3
or the first defender experiment. It uses all nine included attack sessions,
not the terminal-activity-selected subset of windows. As in the original
defender experiment, login start/end metadata defines the evaluation period.
No terminal commands or Windows command-line fields become features.

## Input coverage

Start from the completed 30-second defender extraction. It contains Security
and Sysmon from the four hosts present in all nine sessions and VPC flow logs.
Read additional common Windows channels: scheduled-task events on all four
hosts, System on `dc01` and `srv02`, Application on `srv02` and `srv03`, and
IIS access on `srv02`. Additional Windows features are fixed EventID counts;
IIS contributes only record counts. Five-second event-count bins contain no
message text, IP addresses, ports, usernames, host IDs, or commands.

Other archives include channels that are absent from some sessions, operator
audit/terminal-related records, and experiment-control or infrastructure logs.
They are not included: their availability can reveal the session, they may
contain commands, or they do not represent ordinary defender telemetry. Thus
this is not a claim that every file in every archive was modeled. Additional
channels can be sparse; file presence does not establish complete capture or
distinguish a quiet period from missing events.

Only the existing eligible 30-second windows are used. A 60-, 120-, or
300-second window is eligible only when all constituent, aligned 30-second
windows are eligible. This can disproportionately remove longer windows and
change the evaluated population. Flow `SKIPDATA`, timestamp coverage and
flow-end timing caveats from `DEFENDER_TELEMETRY_EXPERIMENT.md` still apply.
The timing features include fractions of active five-second bins, peak-bin
fraction, coefficient of variation and co-activity. Flow bins use the flow
record's end time and cannot recover timing within an aggregation interval.

## Analysis

Each phase uses combined features and fixed hyperparameters:

1. Logistic regression at 30, 60, 120 and 300 seconds.
2. XGBoost at the same lengths, using the same baseline features.
3. XGBoost with additional channels and timing features.
4. The phase 3 model with SMOTE applied **only within each training fold**.

All use leave-one-session-out evaluation, training-fold standardization,
fixed 0.5 threshold, log-transformed features, equal class/session weights
before resampling, and the same session-label permutations. SMOTE is applied
after training-fold standardization; synthetic minority samples initially
receive the mean weight of the original minority samples, then class weights
are normalized. Equal session weight therefore does not hold exactly after
SMOTE. It does not create independent sessions.

For each feasible configuration, report pooled macro-F1, an interval from
2,000 class-stratified session resamples of the fixed out-of-fold predictions,
AI recall, human attack-window false-positive rate, session accuracy, and the
exact permutation p-value from all 126 session-label assignments. The
bootstrap does not refit models and does not capture model-selection
uncertainty. Apply Holm correction across all 16 planned configurations, using
p=1 for configurations that lack eligible windows for every session. Results
are exploratory: this follow-on was devised after viewing earlier results,
and permutation inference assumes exchangeable sessions. Lab, operator and
collection differences can violate that assumption.

With only 126 possible session-label assignments, the smallest exact p-value is
1/126. Across 16 configurations, the smallest possible first Holm-adjusted
p-value is 16/126, approximately 0.127; none can reach 0.05 in this family.
Additional independent sessions are needed for finer permutation resolution.

The reported human false-positive rate refers to **human attacks**, not benign
SOC traffic. The design does not test discovery of an unknown attack period,
real-time latency, calibration, deployment false-alert rates, or generalization
to new environments. Flow delivery can be delayed. Independent sessions and
benign data are needed for a production-relevant assessment.

## Running

Use the pinned environment from `STUDY3_REPRODUCTION.md`, then install the
additional dependency:

```powershell
& $python -m pip install -r scripts\defender-expanded-requirements.txt
& $python scripts\defender_telemetry_expanded.py extract --source $study --prior $prior --output $output
& $python scripts\defender_telemetry_expanded.py evaluate --output $output --phase windows
& $python scripts\defender_telemetry_expanded.py evaluate --output $output --phase models
& $python scripts\defender_telemetry_expanded.py evaluate --output $output --phase behavior
& $python scripts\defender_telemetry_expanded.py evaluate --output $output --phase smote
& $python scripts\defender_expanded_report.py --output $output
```

`$prior` is the completed first defender experiment output, and `$output` must
be a new directory outside the repository and source data. The extraction
checks the frozen source hashes and both scripts, and later evaluation checks
the extraction hash. A code change requires a fresh extraction. Phase results
are written separately and never overwritten. Feature tables, pseudonymous
session keys, per-session results and predictions are restricted; do not
commit them. The 126 permutations per configuration are CPU work; a GPU is not
required.
