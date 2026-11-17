# EDA run 3

Re-cuts the feature EDA for the research questions and hypotheses as they now stand, in the figure format of the reference praxis. The rule it follows was written before the run: `reports/eda_run3/RULE_BEFORE_RUN.md`.

One command rebuilds the tables and figures and runs the checks:

    S3_LIBS=<folder with SciPy 1.15.3> python3 -I -B code/eda_run3/run_eda_run3.py

- `run3_common.py`: input list and checks of each input, the names used in the paper, plain feature labels.
- `run3_tables.py`: tables R1, R2, R9 to R13 in `reports/eda_run3/tables/`. Feature values from the rows marked `train` only.
- `run3_figures.py`: figures EDA01 to EDA12 and their captions in `reports/eda_run3/figures/`, drawn from tables only.
- `run_eda_run3.py`: runs both, a second time into a temporary folder, and writes `reports/eda_run3/run3_checks.json`.

The Pass 1 and Pass 2 code in `code/eda/` is imported and not edited. Run 3 fits no model and opens no command text, recorder record or audit record.
