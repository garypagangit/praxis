# EXP03 Internal Defensibility Challenge

Generated: 2026-06-19T13:30:07.089222+00:00

Verdict: **SOURCE GATE PASS - SIMULATOR SMOKE PENDING**

| Challenge | Answer |
|---|---|
| Are core repos accessible? | Accessible repos: `4`. |
| Are model checkpoints accessible? | Accessible HF models: `5`. |
| Are all datasets public? | No. At least one LIBERO dataset path is public, but several related robot datasets are gated or unauthorized. |
| Are held-out templates frozen? | Yes. Held-out rows: `16`. |
| Does this prove VLA generalisation? | No. Simulator install and official evaluation are still required. |
| Main weakness | No robot policy inference was run in this gate. |
| Main strength | The next simulation run now has fixed assets, templates, and split roles. |
