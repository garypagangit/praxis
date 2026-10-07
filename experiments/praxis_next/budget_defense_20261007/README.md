# Attack evidence under a fixed review budget

Completed exploratory replay: 600 settings, ten policies, two datasets, three archived fitting seeds, two observation conditions, five budgets. No new data collection or neural fitting. No policy meets the frozen cross-dataset mitigation criterion. THEIA's GIN/local combination is promising but fails clean-performance tolerance and does not transfer to CADETS.

Run `python audit.py` for public arithmetic and algorithm checks. Run `python run.py --scores PATH_TO_ARCHIVED_OUTPUTS` to reproduce metrics from the original local score archives. Requires NumPy and SciPy. The original archives remain local; their SHA-256 hashes are in RESULTS.json. Public aggregates support arithmetic verification, not independent source-label or full-score reproduction. Original model implementation, configuration, provenance and previous graph analyses are in the adjacent repository studies.

Paper: `output/doc/budget_defense_20261007/Gary_Pagan_Budget_Defense_Praxis.docx` and PDF. This is a GWU-style research draft for adviser review, not an approved or submission-ready degree manuscript. Committee details and conferral date are not asserted.

The protocol was committed before this replay, after predecessor test results had already been inspected. This is not preregistered independent confirmation. Batch percentile fusion accesses the full unlabeled evaluation-score distribution; it is not an online detector. One random edge-loss mask is not a chronological outage.

All seven fusion methods and all three individual scores are retained, including failures. Means over fitting seeds are descriptive; there are only two labeled graph evaluations. Node counts are not independent attack counts.
