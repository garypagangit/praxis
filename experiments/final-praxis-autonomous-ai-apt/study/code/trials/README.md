# Study 3 trial code

Implements sections 5 to 9 of `real_lab3_feature_trial_design.md` (approved; amended with F16 and F17
on 2026-11-13). Written fresh for study 3. Needs NumPy, scikit-learn 1.7, SciPy and XGBoost 3; the
versions used are written to the plumbing log and to Freeze 2.

## Run order

From the study folder, with `python3 -I -B`. `S3_LIBS` names the folder the pinned libraries were
installed in, if they are not in the system's own. The shell this was built in stops every command
after three minutes, so the two long runs work in slices: the command is repeated until `status`
prints `COMPLETE`. Shards (`--shard 0/4` to `3/4`) are started side by side.

| # | Command | Writes |
|---|---|---|
| 1 | `run_trials.py plumbing --shard i/4` | `reports/plumbing/parts/` (counts, hashes and times of every task) |
| 2 | `run_trials.py plumbing-log` | `reports/plumbing/PLUMBING_LOG.json`, `plumbing_timing.json` |
| 3 | `run_trials.py freeze2 --confirm` | `reports/FREEZE_2.json`, `reports/freeze2/` (the design as frozen). Only on the user's word |
| 4 | `run_trials.py score --shard i/4` | `results/trials/` (one file for each model of each trial), `results/parts/` |
| 5 | `summarize.py` | `results/tables/`, `results/RESULTS_SUMMARY.md`, `results/summary.json` |

## What is enforced in the code

- **No score before Freeze 2.** `score` and `summarize.py` stop unless `reports/FREEZE_2.json` exists and
  the trial code, the feature tables, the frozen design and the plumbing log still match it.
- **The plumbing run scores nothing.** It fits and calibrates every fold of every trial, predicts no
  held-out session and no test row, and writes counts, hashes and times only. It cannot open the
  test-label files or the description files, and it is closed once Freeze 2 is written.
- **Each trial is scored once.** A result file is never written twice. A stopped task leaves nothing
  behind and is run again.
- **The scored fit is the plumbed fit.** Every task carries a hash of its fitted calibrations; the
  scored run compares it with the plumbing run's.
- **Inputs.** Every input is checked against Freeze 1 (or, for the feature tables, against
  `reports/10_features_checks.json`) before it is read. The evidence folder, `set_aside/` and the
  private key map are refused by name.
- **Column guard.** Only the 60 columns of design section 4 can enter a model, by configuration, and no
  column named for a duration, position, session, stage or label.
- **Fitted inside training sessions only:** medians, scaling, weights, the model, the calibration and
  the threshold. A fold's fitting reads the classes of its training sessions only.

## Files

| File | Holds |
|---|---|
| `trial_common.py` | Inputs, the column guard, configurations, weights, the five models, calibration, the threshold, leave one session out, the inside-session evaluation |
| `run_trials.py` | The task list (trials and the 126 relabelings of the chance baseline), the plumbing run, Freeze 2, the scored run |
| `summarize.py` | The tables of design section 11 from the scored predictions: metrics, session bootstrap, by session, by stage group, chance baseline, hypothesis tests |
| `selftest_fixture.py`, `selftest_checks.py` | A synthetic study tree and the checks run on it before Freeze 2. The scored code was tried on made-up data only |

The tasks: 9 leave-one-session-out trials and 1 inside-session trial for 5 models (50), and 126
relabelings in 2 configurations for 5 models (1,260).
