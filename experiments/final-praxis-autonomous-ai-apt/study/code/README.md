# Study 3 preprocessing code

Implements `real_lab3_preprocessing_design.md` (approved, amendments A1–A17). Python standard library only.
Nothing is ever written inside `AHIR Participant Evidence/`.

## Run order

Each command is run from this folder with `python3 -I`. A step that prints `INCOMPLETE` is run again until it prints `COMPLETE`
(the shell this was built in stops every command after three minutes, so long steps work in slices; the output is the same
however many slices it takes).

| # | Command | Writes |
|---|---|---|
| 1 | `step01_verify.py` | `reports/01_verification_report.json` |
| 2 | `step02_route.py scan`, then `operator`, then `setaside`, then `report` | `set_aside/`, `reports/02_route_report.json`, ledger rows |
| 3 | `step03_clean.py` | `reports/03_clean_report.json`, `reports/03_validator_family_execs_for_review.json`, ledger rows |
| 4 | `step04_commands.py` | `data/cleaned/`, `data/commands/`, `reports/04_commands_report.json`, `reports/04_removed_validator_commands.jsonl`, ledger rows |
| 5 | `step05_windows.py` | `data/windows/w30`, `w60`, `data/labels/`, `data/description/`, `reports/05_windows_report.json` |
| 6 | `step06_split.py` | `data/splits/`, `data/labels/labels_*`, `reports/06_split_report.json` |
| 7 | `step07_leak_audit.py` | `reports/07_leak_audit_report.json` (must be zero hits) |
| 8 | `step08_summary.py` | `reports/08_summary.json`, `reports/PREPROCESSING_RUN_SUMMARY.md` |
| 9 | `step09_freeze.py --confirm` | `reports/FREEZE_1.json` — only after the review before the freeze |

Environment: `S3_WORK` is a scratch folder outside the study folder (default `~/s3_work`). It holds the operator records between
steps 2 and 4, before they are fully cleaned, and is rebuilt from the originals on every run. `S3_OUT` redirects all outputs
(used for development runs).

## Modules

| File | Holds |
|---|---|
| `s3_config.py` | Sessions, login tables with reasons, package layouts, constants |
| `s3_io.py` | Package readers (whole zip, parts read in place, split delivery), hashing, deterministic writers |
| `s3_audit.py` | Audit record groups |
| `s3_clean.py` | Every cleaning pattern of design §6, and the leak-audit patterns built from them |
| `s3_term.py` | Terminal tokens, visible text, the prompt pattern, the screen used for the per-line text rule |
| `s3_commands.py` | Command reconstruction (design §6.7) |

## Files in `data/`

| Path | Holds |
|---|---|
| `cleaned/<session>/<login>.recorder.jsonl`, `.audit.jsonl` | Cleaned classifier input in the collected record shape, event ids kept for the trace |
| `commands/<session>/<login>.commands.jsonl` | The command list (A7). Times are seconds since the login's start; `in_*` and `out_*` point at record numbers of the cleaned recorder file (`i` in the window files) |
| `windows/w30`, `w60` | `windows.csv` (every window, kept or not, with the reason) and one file per login with the records of kept windows; ids removed |
| `labels/` | `sessions.csv`, `logins.csv`, label files for the split, `_private/key_map.csv` |
| `splits/` | `splits_w30.csv`, `splits_w60.csv` |
| `description/` | Description only, never joined to features: elapsed working time and stage of each window, stage acceptances, lab range |
