COMMAND/RESULT QUALIFICATION AND NEXT COMPARISON
October 12, 2026

Decision: proceed with measurement validation, not another detector fit yet.
Published data provide usable submission/result pairs. Whole-submission handling
increases exploratory matched coverage, but the planned five-submission comparison
has only six human and six AI sessions across six tasks and three human operators.
No new model, operational detection claim, or analyst-benefit claim is made.

Read FINDINGS.txt for evidence and limits; COMPARISON_PROTOCOL.txt for the next
distinct hypothesis and controls; NOVELTY_REVIEW.txt for prior-art boundaries.
results/QUALIFICATION.json is the authoritative machine-readable summary.
PAIR_AUDIT, SESSION_AUDIT and TRANSITION_AUDIT retain hashes, exclusions and counts,
not raw commands/results. MATCHED_FIRST5_SESSIONS identifies the small fixed-prefix
cohort. SOURCES binds the local source archives and members.

Reproduction (Python standard library, from this directory):
  python -m unittest discover -p test_pair_rules.py -v
  python qualify_pairs.py --raw C:/w/px120_lyptus_20261007 --members C:/w/px122_lyptus_20261007 --prior C:/w/ai_operator_20261007/experiments/praxis_next
  python validate_artifacts.py

Raw archives and inherited replay records are local dependencies, not bundled.
The manifests retain original source locations and hashes. Relocation requires
updating local paths in a copy of those manifests, while preserving source hashes.
Unit tests and the aggregate validator run without raw datasets. The full audit
requires the bound sources. Dataset contents are treated as inert text.

INITIAL_QUALIFICATION.json preserves the first development audit. The final rule
also subtracts earlier retained results when testing whether a literal is new;
the initial version only subtracted commands. The final audit additionally reports
contiguous prefix coverage. These are disclosed measurement corrections, not
post-hoc changes to a classifier success gate. All cases remain development data.
