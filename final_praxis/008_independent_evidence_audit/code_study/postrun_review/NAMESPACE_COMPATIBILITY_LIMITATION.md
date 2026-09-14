# Original-test helper namespace limitation

This limitation was identified after the main study source and cohort were frozen.
No frozen code, eligibility labels or study assignments were changed.

The released original tests directly call `poly` for Python/32, `encode_cyclic`
for Python/38 and `encode_shift` for Python/50. These helpers exist in the canonical
program modules. The frozen `worker.original_check` loads the program but runs the
test module in a new namespace containing only the entry-point function and the
assertion tracer. A direct helper lookup inside that test namespace therefore
raises `NameError`.

Python/38 and Python/50 were excluded solely for this original-test compatibility
failure. Python/32 was also excluded for reserved-test results. These original-test
exceptions are not evidence of canonical-program semantic defects.

The independent follow-up confirms that every one of the 135 included tasks has
a passing canonical original suite, a fully passing canonical reserved suite, a
fully passing reference reserved suite, and a demonstrated buggy reserved failure.
The included cohort contains 34 development and 101 heldout tasks. Conclusions
remain conditional on this frozen cohort; they do not generalize to every released
task merely because all 164 task IDs remain in assignment accounting.

Generated proposal Y1 is determined from reserved tests. Its original-test trace
is diagnostic and does not define Y1, so this namespace issue must not be mistaken
for an additional generated-outcome gate.

A future version should preserve the trusted program's helper namespace when
running its original tests, with an explicit policy for test/tracer-name collisions
and new positive/negative controls. Such a repair requires separately versioned
qualification and cannot be retroactively applied to this frozen study.

Evidence and exact source/data hashes are in `QUALIFICATION_FOLLOWUP.json` and
`../completed_qualification/RESULTS.json`. No downloaded program was executed by
the follow-up reviewer; the helper dependency was inspected using source ASTs.
