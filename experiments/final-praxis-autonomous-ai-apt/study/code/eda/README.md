# Study 3 EDA code

Implements `real_lab3_eda_handoff.md`. Separate from the preprocessing code in `code/`; the only thing it takes
from there is the leak-audit pattern list in `s3_clean.py`, which the output check reuses.

## Run

From the study folder, one command rebuilds a pass:

    python3 -I -B code/eda/run_eda.py pass1

`-B` keeps Python from writing a `__pycache__` folder. Needs Matplotlib and NumPy (Pass 2 adds pandas and SciPy).

## What Pass 1 does

| Step | Script | Reads | Writes |
|---|---|---|---|
| Tables | `pass1_tables.py` | Step reports 05, 06, 08; `data/labels/sessions.csv`; `data/description/`; `data/splits/` | `reports/eda/tables/` T1, T2, T3 and the tables behind E2, E3, E6; `reports/eda/pass1_tables_log.json` |
| Figures | `pass1_figures.py` | `reports/eda/tables/` only | `reports/eda/figures/` E2, E3, E4, E6 as PNG (300 dpi) and SVG; `captions_pass1.md`; `reports/eda/pass1_figures_log.json` |
| Checks | `run_eda.py` | The outputs | `reports/eda/pass1_checks.json` |

## Rules built into the code (handoff section 1)

- Every input is on a fixed list, is checked against `reports/FREEZE_1.json` before it is read, and is logged with
  its hash. The evidence folder, `set_aside/`, the private key map and the test-label files are refused by name.
- Pass 1 reads, for each window, only: window id, session key, login order, elapsed working time, stage group,
  the kept flag and the split. Class comes from the session table. The session labels (P001 ...) come from the
  windows step report, so the private key map is not needed.
- T1 takes its counts from the step reports. Every count that can be compared with a step report or the split
  file is compared, and the run stops on a mismatch.
- Figures are drawn from the CSV tables, never from the data.
- Nothing is written outside `reports/eda/`. The second run of the rerun check writes to a temporary folder
  outside the study folder and is deleted.
- The outputs carry no time stamp, so a rerun gives the same bytes.

`S3_ROOT` and `EDA_OUT` redirect the study folder and the output folder (used by the rerun check).
