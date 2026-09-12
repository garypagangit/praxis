# MiCRo logic qualification: independent audit

**Status:** COMPLETE. **Decision:** DO_NOT_ADVANCE_CURRENT_QUALIFICATION.

Primary scoring is frozen flexible exact match, including truncated outputs. Pilot results are descriptive only.

| Test arm | Completed | Flexible correct | Strict correct | Numeric extracted | Truncated |
|---|---:|---:|---:|---:|---:|
| intact | 256/256 | 80 | 2 | 253 | 48 |
| logic_ablation | 256/256 | 13 | 2 | 255 | 79 |
| social_ablation | 256/256 | 91 | 3 | 251 | 47 |

Paired effects are intact minus ablated accuracy; positive values indicate lost ability after ablation.

- flexible/intact_minus_logic_ablation: 26.17 percentage points [95% paired bootstrap 20.31, 32.03], n=256; correct-to-wrong=72, wrong-to-correct=5.
- flexible/intact_minus_social_ablation: -4.30 percentage points [95% paired bootstrap -7.81, -0.78], n=256; correct-to-wrong=6, wrong-to-correct=17.
- flexible/social_minus_logic: 30.47 percentage points [95% paired bootstrap 24.22, 36.33], n=256; correct-to-wrong=83, wrong-to-correct=5.

Jointly nontruncated sensitivity (descriptive; outcome-dependent subset; never changes gates):

- intact_minus_logic_ablation: 30.77 percentage points; n=143.
- intact_minus_social_ablation: -4.12 percentage points; n=194.

Gate components:

- complete_frozen_cohort: PASS
- all_technical_checks: PASS
- intact_accuracy_at_least_25pct: PASS
- intact_truncation_at_most_10pct: FAIL
- intact_extraction_at_least_90pct: PASS
- logic_loss_at_least_10pp: PASS
- paired_ci_lower_positive: PASS

Integrity errors: 0; missing cells: 0.

All required technical checks must pass. Social ablation is diagnostic, not an additional gate. A pass establishes a useful-specialist prerequisite only.

Limitations:

- No novelty, containment, or fault-transfer efficacy claim.
- Flexible extraction may reward the last number in unfinished reasoning; truncation remains separate.
- Independent audit checks IDs, hashes, metadata and arithmetic; it does not re-decode token IDs or inspect weight tensors.
- Question uncertainty is not uncertainty across model families, seeds or measurement protocols.
- Incomplete/invalid cohorts and pilot results cannot pass qualification.
