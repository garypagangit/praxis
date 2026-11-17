# Study 3 EDA code, Pass 2

Implements section 6 of `real_lab3_eda_handoff.md`, as amended by its section 12a: Pass 2 is run after the
trials, as a report only. It cannot correct, add or drop a feature.

The Pass 1 files in this folder (`eda_common.py`, `pass1_tables.py`, `pass1_figures.py`, `run_eda.py`,
`README.md`) are part of Freeze 2 and are not edited. Pass 2 is these files:

| File | Holds |
|---|---|
| `pass2_common.py` | Inputs checked against Freeze 1 or Freeze 2; the loader of the rows marked `train`; the rank statistics |
| `pass2_tables.py` | T4 to T9 and the tables the figures are drawn from |
| `pass2_figures.py` | E1, E2 (tier lines filled in), E5, E7 to E12, and the captions |
| `run_eda_pass2.py` | One command for the pass, and the checks |
| `pass2_review_notes.json` | What the review of each flagged feature found; merged into T5 |

## Run

From the study folder:

    S3_LIBS=<folder with SciPy> python3 -I -B code/eda/run_eda_pass2.py

Needs Matplotlib, NumPy and SciPy (pandas is not used). SciPy is not installed in the shell; it is installed to a folder
outside the study folder and named with `S3_LIBS`, as for the trials:
`pip install --no-deps --target <folder> scipy==1.15.3`.

## What Pass 2 does

| Step | Script | Reads | Writes |
|---|---|---|---|
| Tables | `pass2_tables.py` | Split files, session table, description files, feature tables, column files and per-command tables (30 s and 60 s); the window files of the training windows (30 s); step reports 05 and 10; Pass 1's T1, T3 and E2 overview | `reports/eda/tables/` T4 to T9 and the E tables; `reports/eda/pass2_tables_log.json` |
| Figures | `pass2_figures.py` | `reports/eda/tables/` only | `reports/eda/figures/` as PNG (300 dpi) and SVG; `captions_pass2.md`; `reports/eda/pass2_figures_log.json` |
| Checks | `run_eda_pass2.py` | The outputs | `reports/eda/pass2_checks.json` |

## Rules built into the code (handoff section 1)

- Every input is on a fixed list and is checked against Freeze 1 or Freeze 2 before it is read. The evidence
  folder, `set_aside/`, the private key map and the test-label files are refused by name. `results/` is not read.
- Feature values, command text and window records are read from rows marked `train` in the frozen split file and
  from no other row. The loader logs the row count of every split value and stops if a row of another split is
  present. A program start that fell in a window that is not a training row is not counted.
- Class comes from the session table, the stage group and the lab range from the description files. The session
  labels (P001 ...) come from the windows step report; the private key map is not opened.
- No model is fitted. Every statistic is a rank statistic of one or two columns.
- Nothing is written outside `reports/eda/`, and no Pass 1 output is rewritten: the E2 with the tier lines is a
  new file. The second run of the rerun check writes to a temporary folder outside the study folder.
- The outputs carry no time stamp, so a rerun gives the same bytes.
- E1 shows text from two training windows. The windows are picked by a fixed rule and a screen, not by reading
  them, and the figure is to be read by a person before use. `E1_data_example_masked` is the same figure with every
  letter and digit masked; it is the copy that was looked at when the layout was checked.
