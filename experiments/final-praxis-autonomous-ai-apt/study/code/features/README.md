# Study 3 feature step

Implements sections 3 and 4 of `real_lab3_feature_trial_design.md`: 60 columns in four tiers
(behavior 18, command content 14, context 12, input channel 16), for 30-second and 60-second windows.

## Run

From the study folder:

    python3 -I -B code/features/run_features.py

This builds the tables, builds them a second time in a temporary folder and compares hashes, runs the
preprocessing's leak-audit patterns over the new files, and writes the review file.
`step10_features.py` alone builds the tables without the checks.

## Reads

Only `data/`, each file checked against `reports/FREEZE_1.json` before it is read:

| File | Used for |
|---|---|
| `data/windows/w30|w60/windows.csv` | Window id, session key, login key, window index, kept flag and the three record counts (for checks). The stage columns are not kept in memory |
| `data/windows/w30|w60/<session>/<login>.jsonl` | Program starts of the kept windows |
| `data/cleaned/<session>/<login>.recorder.jsonl` | The login's input and output records |
| `data/commands/<session>/<login>.commands.jsonl` | The command list written by the preprocessing. Commands are not found again |

Never read: labels, split files, stage, the description files, the audit files, `set_aside/`, the evidence folder.
The code refuses those paths by name.

## Writes

| File | Holds |
|---|---|
| `data/features/w30|w60/features.csv` | One row for each kept window: `window_id` and the 60 columns. Undefined is empty |
| `data/features/w30|w60/feature_columns.json` | Tier, kind, definition and undefined rule of every column, with input and output hashes |
| `data/features/w30|w60/per_command.jsonl` | For the EDA: command text, entry style, programs started. **Holds command text** |
| `reports/10_features_report.json` | Counts, checks, undefined shares for each session, hashes |
| `reports/10_features_checks.json` | Rerun comparison, leak audit, the list of outputs |
| `reports/10_features_review_windows.md` | Five windows from each session beside their feature rows. **Holds command text**; read by a person, in place |

The outputs carry no time stamp, so a rerun gives the same bytes. `S3_FEATURE_OUT` redirects the outputs (used by the rerun check).

The terminal tokens (`s3_term.py`) and the leak-audit patterns (`s3_clean.py`) are imported from the frozen
preprocessing code so that program output and the audit are defined the same way in both steps.
