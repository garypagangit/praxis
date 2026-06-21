# EXP03 LIBERO Data Gate Internal Defensibility Challenge

Generated: 2026-06-21T11:07:20.529300+00:00

Verdict: **FINAL STOP/REFRAME - PUBLIC DATA LACKS LANGUAGE AND SIMULATOR SUPPORT**

| Defense question | Answer |
|---|---|
| Is there a public robot data path? | Yes. `lerobot/libero_10` exposes `101469` frames and `379` episodes. |
| Does the public path contain natural-language instructions? | No. The inspected data columns and `meta/tasks.parquet` do not include instruction text. |
| Are official simulator/model imports ready locally? | No. Required imports available: `0/5`. |
| Can RQ1-RQ3 be answered from this gate? | No. The missing language metadata and simulator stack block success-rate evaluation. |
| Final decision | Stop/reframe for this cycle; do not claim VLA instruction-diversity generalisation. |
