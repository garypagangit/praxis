# EXP04 HaluEval NLI Internal Defensibility Challenge

Generated: 2026-06-19T13:24:39.429636+00:00

Verdict: **MIXED - NEEDS NEXT GATE**

| Challenge | Answer |
|---|---|
| Were validation and strict holdout separated? | Yes. Validation used HaluEval QA; strict holdout used HaluEval dialogue. |
| Did threshold selection touch holdout? | No. NLI threshold `0.65` was selected on validation only. |
| Did NLI beat lexical? | F1 delta `0.0156`. |
| Did the holdout F1 clear target? | Holdout NLI F1 `0.6878`. |
| Are raw dataset responses committed? | No. Prediction rows use hashes, lengths, labels, probabilities, and metrics only. |
| Main weakness | NLI is not KG reasoning and may reward lexical support rather than full factual entailment. |
| Main strength | It adds a real external HaluEval dialogue holdout after the Wikidata smoke gate. |
