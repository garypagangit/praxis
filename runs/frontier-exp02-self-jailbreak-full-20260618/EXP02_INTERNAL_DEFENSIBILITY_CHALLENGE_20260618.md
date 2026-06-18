# EXP02 Internal Defensibility Challenge

Generated: 2026-06-18T22:17:08.622618+00:00

Verdict: **MIXED / NEEDS NEXT GATE**

| Challenge | Answer |
|---|---|
| Did the run use strict holdouts? | Yes. JailbreakBench harmful and benign behavior splits were held out from WildJailbreak prompt-detector training. |
| Was raw harmful text committed? | No. Prediction artifacts contain hashes, lengths, labels, probabilities, and metrics only. |
| Did the prompt detector preserve benign controls? | Benign false-refusal mean `0.6900`. |
| Did the response-step detector catch unsafe responses? | Unsafe recall mean `0.8158`. |
| Does step-level beat output-only? | It provides earlier interruption: caught-unsafe exposure fraction `0.2370` vs output-only `1.0000`. |
| Is this a final live-model safety claim? | No. It is a dataset-based publishable pilot; live open-model validation is still required. |
| Main weakness | Response-step labels are response-level human labels applied to sentence scans; future work should add manually labeled boundary steps. |
| Main strength | Strong redaction discipline, strict benign controls, and measurable intervention utility without unsafe generation. |
