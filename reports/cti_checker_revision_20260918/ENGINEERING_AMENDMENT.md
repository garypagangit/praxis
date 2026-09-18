# Input validation correction before calibration scoring

The first calibration-scoring invocation passed the same eight synthetic qualification checks, then stopped during whole-file input validation. No dataset pair was scored and no calibration score file was produced.

One historical question, `cti_mcq_56`, contains an empty displayed D option. The two options required for its saved answer comparisons are A and C, both nonempty. The strict all-four-nonempty validator was incompatible with this existing record.

The correction retains the historical question and all original option strings unchanged. It requires exactly the A-D option keys with string values, and requires every option actually requested for scoring to be nonempty. Default all-four scoring still rejects empty options. It does not drop a question, change an answer, change the semantic hypothesis, change a threshold, or inspect any new score.

The original successful `CALIBRATION_QUALIFICATION.json` is preserved. The corrected invocation records fresh qualification in `CALIBRATION_QUALIFICATION_R2.json`. This is an input-contract correction before model scoring, not a repeat selected by benchmark accuracy. The original scorer hash is retained in `NLI_QUALIFICATION_RECEIPT.json`; subsequent receipts bind the corrected scorer.
