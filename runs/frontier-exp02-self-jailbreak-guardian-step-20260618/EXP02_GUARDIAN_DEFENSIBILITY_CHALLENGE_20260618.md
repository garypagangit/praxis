# EXP02 Guardian Internal Defensibility Challenge

Generated: 2026-06-18T22:44:03.680801+00:00

Verdict: **MIXED / NEEDS NEXT GATE**

| Challenge | Answer |
|---|---|
| Did the gate avoid committing raw harmful text? | Yes. Redacted rows contain hashes, lengths, parsed labels, probabilities, and metrics only. |
| Did prompt guarding preserve benign controls? | Benign false-refusal mean `0.8700`. |
| Did response-prefix guarding catch unsafe responses? | Unsafe recall mean `1.0000`. |
| Did it block safe responses? | Safe block mean `0.1818`. |
| Does it beat output-only timing? | Caught unsafe exposure fraction `0.1310` vs output-only `1.0000`. |
| Is this a live model claim? | No. It is a benchmark-response guardian gate. A live open-model run remains external validity. |
