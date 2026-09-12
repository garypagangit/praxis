# MiCRo logic qualification: independent audit

**Status:** PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY. **Decision:** DO_NOT_ADVANCE_CURRENT_QUALIFICATION.

Primary scoring is frozen flexible exact match, including truncated outputs. Pilot results are descriptive only.

| Test arm | Completed | Flexible correct | Strict correct | Numeric extracted | Truncated |
|---|---:|---:|---:|---:|---:|
| intact | 0/256 | 0 | 0 | 0 | 0 |
| logic_ablation | 0/256 | 0 | 0 | 0 | 0 |
| social_ablation | 0/256 | 0 | 0 | 0 | 0 |

Paired effects are intact minus ablated accuracy; positive values indicate lost ability after ablation.


Jointly nontruncated sensitivity (descriptive; outcome-dependent subset; never changes gates):

- intact_minus_logic_ablation: no eligible paired responses.
- intact_minus_social_ablation: no eligible paired responses.

Gate components:

- complete_frozen_cohort: FAIL
- all_technical_checks: FAIL
- intact_accuracy_at_least_25pct: FAIL
- intact_truncation_at_most_10pct: PASS
- intact_extraction_at_least_90pct: FAIL
- logic_loss_at_least_10pp: FAIL
- paired_ci_lower_positive: FAIL

Integrity errors: 0; missing cells: 816.

All required technical checks must pass. Social ablation is diagnostic, not an additional gate. A pass establishes a useful-specialist prerequisite only.

Limitations:

- No novelty, containment, or fault-transfer efficacy claim.
- Flexible extraction may reward the last number in unfinished reasoning; truncation remains separate.
- Independent audit checks IDs, hashes, metadata and arithmetic; it does not re-decode token IDs or inspect weight tensors.
- Question uncertainty is not uncertainty across model families, seeds or measurement protocols.
- Incomplete/invalid cohorts and pilot results cannot pass qualification.
