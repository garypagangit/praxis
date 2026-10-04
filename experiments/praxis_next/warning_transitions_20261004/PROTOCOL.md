# PX-106: Warning loss versus exact-class negative flips

Status: exposed-data, descriptive follow-up. This protocol precedes this calculation, but the underlying results have already informed the research. It is not a prospective validation.

Question: how much warning loss is omitted by counting only previously correct attack-stage predictions that become incorrect?

Use every saved PX-081 entropy/error-focused pair: three fitting seeds, three evidence conditions and three budgets (27 pairs, identical 208,094 rows). Entropy is the reference; error-focused is the candidate. Do not select pairs after observing this calculation. Preserve the four native classes and all three attack stages separately.

For each stage, retain the complete reference-prediction by candidate-prediction transition matrix. Count: exact-to-benign losses; wrong-attack-to-benign losses; benign-to-attack gains; all warning losses; exact-class negative flips; and both stage recalls. Ordinary exact-class negative flips include exact-to-wrong-attack changes but omit wrong-attack-to-benign changes. Binary attack-versus-benign negative flips capture all warning losses; we claim no advantage over that established binary measurement.

Report macro-F1, benign false alerts, and net warning change. Verify new warnings minus lost warnings equals the difference in total warnings. Report the clean, budget-three comparison per seed as the existing primary example; retain every other cell in JSON/CSV. Do not pool repeated rows as independent attacks or perform flow-level significance tests.

Also apply the already stated illustrative review tolerances descriptively to these test outcomes: F1 must rise, no supported attack stage may lose more than 1 percentage point of warning recall, and benign FPR may rise by at most 0.1 percentage point. This is not the calibration-only acceptance procedure, a tuned policy, or a claim of prospective gating effectiveness.

No fitting, parameter search, paid compute, human participants or deployment. Freeze script, protocol and source hashes before calculation. Independently reconstruct all reported count matrices and metrics from the saved predictions. Report unfavorable and zero results.
