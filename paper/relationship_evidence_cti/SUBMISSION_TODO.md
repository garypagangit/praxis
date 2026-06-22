# Praxis 07 Submission TODO

Updated: 2026-06-22

## Immediate

- Done: added a compact pipeline figure: CTI-MCQ row -> ATT&CK evidence retrieval -> strict answer parser.
- Done: added an illustrative locked-slice row where relationship evidence supplies the answer-bearing fact.
- Done: added a GitHub Actions PDF build path for `main.tex` and `thesis_chapter.tex`.
- Next: inspect the CI PDF artifacts for page breaks, table density, and whether the example row should move to appendix for a target venue.
- Decide whether this is a thesis section, workshop paper, or appendix result paired with Praxis 06.

## Do Not Do

- Do not run LoRD extraction from this result chain.
- Do not rename the result back to a pure relationship-causality claim.
- Do not hide the slice audit soft pass.
- Do not drop invalid outputs from any table.

## Optional Robustness

- External-validity replication on another CTI QA set if a clean public option is available.
- Newer ATT&CK snapshot audit if venue reviewers ask about snapshot age.
- Token-budget-matched ablation only if the mechanism claim becomes central.
