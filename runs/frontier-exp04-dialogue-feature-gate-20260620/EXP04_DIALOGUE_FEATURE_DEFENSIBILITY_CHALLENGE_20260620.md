# EXP04 Dialogue Feature Gate Internal Defensibility Challenge

Generated: 2026-06-20T10:01:54.367277+00:00

Verdict: **MIXED - RESPONSE ARTIFACT BASELINE WINS**

| Defense question | Answer |
|---|---|
| Are train, validation, test, and strict holdout separated? | Yes. Split is deterministic by underlying dialogue row, and paired responses stay in the same split. |
| Did threshold or hyperparameter selection touch strict holdout? | No. Model selection used validation metrics only. |
| Does the evidence model clear the F1 target? | Evidence-plus-numeric strict holdout F1 is `0.7215`. |
| Does the evidence model beat response-only artifacts? | No. Evidence-plus-numeric F1 delta over response-only is `-0.0620`. |
| Does it beat numeric novelty alone? | Yes. Evidence-plus-numeric F1 delta over numeric-only is `0.0252`. |
| Are raw HaluEval rows committed? | No. Output predictions contain hashes, lengths, labels, scores, and metrics only. |
| Publishability decision | Not as a positive EXP04 result. A committee can fairly argue that the current signal is an artifact detector. |
