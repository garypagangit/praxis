# Human vs. Autonomous AI Operator Classification in Advanced Persistent Threat Intrusions

Code and records that accompany the praxis of the same name (Gary Pagan, The George Washington University, 2026).
The study classifies 30-second windows of operator-host telemetry as human or AI, from nine sessions of a seven-stage,
APT29-style exercise on a GOAD range: five human participants and four AI-agent sessions.

This repository holds what Appendix B and Appendix D of the praxis say it holds:

| Praxis item | Where it is |
|---|---|
| Preprocessing code, version 1.1 (Python standard library only) | `code/step01_verify.py` to `code/step09_freeze.py`, `code/s3_*.py`, `code/README.md` |
| Feature code, version 1.1 (60 features, Appendix A) | `code/features/` |
| Trial code, version 1.0 (five classifiers, leave one session out, chance baseline) | `code/trials/` |
| Exploratory data analysis (Section 4.3, Tables A-3 and A-4) | `code/eda/` (passes 1 and 2, imported unchanged), `code/eda_run3/` |
| Test within stage groups, version 1.0 | `code/h2_stage/` |
| Model interpretation (SHAP), version 1.0 | `code/h2_features/` |
| Paired tests, version 1.0 | `code/h1_h3_tests/` |
| What was fixed before scoring | `reports/FREEZE_1.json`, `reports/FREEZE_2.json`, `reports/freeze2/` (the design documents as frozen), `real_lab3_preprocessing_design.md` |
| The written rule of each analysis made after scoring | `results_h2_stage/H2_RULE_BEFORE_RUN.md`, `results_h2_features/H2_FEATURES_RULE_BEFORE_RUN.md`, `results_h2_features/five_classifiers/RULE_ADDENDUM_BEFORE_RUN.md`, `results_h1_h3/RULES_AS_DECIDED.md`, `reports/eda_run3/RULE_BEFORE_RUN.md` |
| Hypotheses, with their criteria and outcomes | `results/tables/T_hypotheses.csv`, `results_h1_h3/tables/`, `results_h2_stage/tables/T_h2_verdict.csv` |
| Hashes kept with each result | `*_checks.json` beside each rule, and `reports/10_features_checks.json` |
| Starting prompt, credentials and connection details removed (Appendix D) | `prompt/starting_prompt_redacted.md` |

## What is not here, and why

The raw session packages hold terminal recordings and are restricted (praxis, Appendix B and Appendix E.5). The cleaned
records, the command lists, the per-window record files and the per-command feature file hold command text, which can
include lab credentials, so they stay with the evidence steward too. The key that links session keys (`s_...`) to
participant codes is private. None of these files is needed to read the code, the frozen design or the rules, and the
hashes in the freeze records let anyone who is given access confirm that the restricted files are the ones that were used.

Because those inputs are absent, the pipeline cannot be rerun from this repository alone: the preprocessing reads the
restricted packages, and every later step checks its inputs against Freeze 1 or Freeze 2 and stops if a file is missing
or changed.

## Environment

Python 3.10.12 with the pinned versions in `requirements.txt` (Table B-1). The random seed is 42. The run order and
working folder of each step are in `code/README.md` (preprocessing), `code/features/README.md`, `code/trials/README.md`
and the docstring at the top of each analysis script.

## Checking the freeze records

Each freeze record lists the size and SHA-256 hash of every file it fixed. To confirm that the code here is the code
that was frozen:

```python
import hashlib, json
freeze = json.load(open("reports/FREEZE_2.json"))
for path, entry in freeze["files"].items():
    if path.startswith("code/"):
        ok = hashlib.sha256(open(path, "rb").read()).hexdigest() == entry["sha256"]
        print("OK " if ok else "CHANGED", path)
```

## Names used in the code

The code and its outputs name the lab ranges by their build names. The praxis calls them A, B and C:

| Praxis (Table 3-4) | Code    |
| ------------------ | ------- |
| A (October 31)     | AHIR-01 |
| B (November 7)     | AHIR-03 |
| C (November 7)     | AHIR-01 |

Sessions appear by participant code (P001 to P011) in `code/s3_config.py`, as in Table 3-4, and by a session key
(`s_...`) in every output after preprocessing.

## Starting prompt

`prompt/starting_prompt_redacted.md` is the standard prompt of 130 non-blank lines, as the AI harness delivered it.
The participant code, account name, host address and password are replaced by bracketed placeholders; nothing else is
changed. Session P010 received a 128-line version without two rule lines of this one: "Do not display or expose
credentials in research reports." and "Do not access administrative answer databases, application source code, hidden
validator files, or another participant's environment." (praxis, Appendix F).
