# EXP04 Internal Defensibility Challenge

Generated: 2026-06-19T13:19:48.727141+00:00

Verdict: **PASS - READY FOR FULL EXP04 GATE**

| Challenge | Answer |
|---|---|
| Did the run use strict holdout rows? | Yes. Strict holdout rows: `36`. |
| Was KG evidence available? | Evidence coverage mean `1.0000`. |
| Did the verifier beat a baseline? | KG F1 `1.0000` vs always-supported F1 `0.0000`. |
| Is there a compounding signal? | Turn-3 minus turn-1 hallucination rate `0.2500`. |
| Does this prove live LLM hallucination reduction? | No. This is a controlled KG smoke gate; live model outputs remain required. |
| Main weakness | The first gate uses templated claims rather than natural model generations. |
| Main strength | Every claim has explicit QID/PID/object evidence and a transparent supported/refuted decision. |
