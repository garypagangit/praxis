# PX-092 — Warning-Preserving OR-Gate: Generalization, Seed-Count and Adversity

[Findings and hypothesis outcomes](FINDINGS.md) | [Part A: existing predictions](partA/RESULTS.md) | [Part B: seed curve](partB/RESULTS.md) | [Part C: adapted AIT](partC/RESULTS.md) | [Independent audit](AUDIT.json)

The user-supplied [protocol](PROTOCOL.md) is preserved byte-for-byte. [Execution clarifications](EXECUTION_NOTES.md) resolve the seven-fit limit, shared acquisition schedule, budget-infeasible reference and current-only fallback before execution. These and all executable experiment/audit/report sources were frozen in `7f55a9d` before any PX-092 result or new fit. No hypothesis threshold was changed.

## Reading the results

- Parts A and B are development evaluations of previously examined UNRAVELED rows. H2 repeats the known PX-086 result.
- Part C uses already fitted AIT models on Wilson and Harrison, held out from those models' training. These executions were examined in earlier work; this is adapted execution-disjoint evidence, not a newly collected or previously unseen validation dataset.
- `best_single` is a test-label-informed exfiltration-recall comparator, with false-alert and member-order tie breaking. Different executions can select different best seeds. It is not a deployable selection policy.
- `overlap_ratio` is the OR false-alert overlap for the model set, repeated on its mean/best-single rows for comparison. Undefined means no constituent false alerts. False-alert overlap alone does not determine whether the absolute alert burden is acceptable.
- Nominal model evaluations and evidence acquisition are different costs. Seeds share each row's evidence. No measured inference speed or analyst benefit is claimed.
- A4 is explicitly a full-evidence, availability-unconstrained reference with cost 3. Its budget-1/2 rows cannot be deployed within those budgets.
- Part B includes 120 unique triples. CSV contains OR and mean rows for each triple; the 240 rows do not mean 240 independent triples.

Every reported cell includes all members, constituent metrics, reference-policy recovery/loss counts, per-row decision hashes and identity/label hashes in `part*/GROUPS.json.gz`. Per-row decisions and raw data remain private under `C:/w/px092_or_gate_20260930` and the original data roots. Seven fitted model files and selected training indices are preserved there. Aggregate CSV/Markdown/JSON outputs are committed to Git.

## Reproduction

Use `C:/w/praxis_full_release_20260927_env/Scripts/python.exe`, with the original private data paths in `common.py`. Six synthetic boundary tests run through `python -m unittest discover -s <this-directory> -p test_px092.py`.

The original execution order was: create and commit FREEZE.json; run `replay.py partA`, `replay.py partC`, and `refit.py` as concurrent local CPU jobs; then `replay.py partB`; then `audit_px092.py`; then `report.py`. Seven new final roles fits were permitted and no new OOF/selector fits were made. No cloud or model API was used.

`publish.py` subsequently created the seed-curve figure, compute receipt and registry entry. Final prose interpretation in FINDINGS.md was reviewed and expanded after the generated tables; rerunning report.py regenerates its numerical core but does not preserve those editorial additions. Hypothesis decisions and frozen executable sources were not edited after execution.

Completed runs are protected against overwriting. Reproduction requires a fresh private output directory and a documented path amendment rather than deleting original outputs. `audit_px092.py` independently rebuilds decisions from original probability arrays, reconstructs acquisition costs and comparison policies, checks source manifests/identities and reproduces all seven new models' full test probabilities. It imports neither the replay nor common module. To rerun the audit from a Git-only checkout with private data available, first decompress each `GROUPS.json.gz` to its adjacent `GROUPS.json`.
