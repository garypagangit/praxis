# Completion-format pilot: final automated review

**Status:** COMPLETE. **Decision:** DO_NOT_ADVANCE_CURRENT_QUALIFICATION.

All 32 TRAIN questions were assigned to both formats. Both use the intact model. Raw is diagnostic; chat alone determines the fixed pilot gate.

| Format | Validated | Flexible correct | Nontruncated correct | Strict correct | Numeric extracted | Truncated |
|---|---:|---:|---:|---:|---:|---:|
| raw | 32/32 | 10 | 10 | 0 | 32 | 3 |
| chat | 32/32 | 9 | 9 | 0 | 32 | 7 |

Registered pilot gates:

- complete_frozen_64_cell_cohort: PASS
- all_technical_checks: PASS
- chat_truncated_at_most_3_of_32: FAIL
- chat_numeric_extracted_at_least_29_of_32: PASS
- chat_nontruncated_correct_at_least_8_of_32: PASS

Paired diagnostics (never choose the winning format or change the gate):

- chat_minus_raw_flexible: -3.12 percentage points [95% paired bootstrap -21.88, 15.62], n=32.
- chat_minus_raw_completed_correct: -3.12 percentage points [95% paired bootstrap -21.88, 15.62], n=32.
- raw_minus_chat_truncation: -12.50 percentage points [95% paired bootstrap -28.12, 0.00], n=32.

Integrity errors: 0; numerical-detail errors: 0; missing cells: 0.

A passing pilot permits a separately preregistered fresh-test qualification. It does not approve a primary Praxis investment or automatically start another study.

Limitations:

- This is a training-split feasibility pilot, not a held-out efficacy or novelty result.
- Raw is diagnostic only; it cannot replace a failed chat candidate.
- Pilot gates do not prove a population truncation rate below 10%.
- Chat text is independently rendered here; token IDs are hashed and compared to the frozen manifest, not independently decoded by this standard-library audit.
- Question-bootstrap intervals do not cover model seeds or families.
- No automatic follow-up inference is permitted by this pilot result.
