# Final Praxis 002 current execution status

Updated 2026-09-08. **DISCOVERY COMPLETE; FROZEN DETERMINATION: NEGATIVE.**

- Refreshed source-grounded novelty review and prospective implementation amendment completed.
- All four arms, six error families, 60 paired base scenarios / 120 conditions and 480 workflow units are implemented.
- Deterministic fixture gate: **144/144 PASS**, plus seven additional fixture-path checks.
- Seven focused statistical-gate and raw-audit tests: **PASS**.
- Preflight: **PASS**; scenario, fixture, source, runtime-adapter and protocol hashes bound.
- Protocol SHA-256: `9722937c2f6cf56f722980595e7960c3a7e1680c7abc670c21b786ee52e4978e`.
- Real infrastructure pilot: **16/16 workflows completed; independent verification PASS**.
- Supplemental pilot exact-request audit: **40/40 real generations PASS**.
- Frozen discovery: **480/480 workflows completed**, with **1,164 real generations**; independent raw-record audit **PASS**. A separate local read-only reconstruction reproduced all rows, bootstrap intervals and gate outcomes exactly.
- Supplemental discovery exact-request audit: **1,164/1,164 PASS**, including system/policy/case/parent messages and unique request IDs. Tokenizer-template binding is not part of the local audit.
- H1, H3, H4, phenomenon and integrity gates: **PASS**. H2: **FAIL** because all arms achieved 51/60 clean successes (85%), below the unchanged 90% absolute floor. A0-to-A3 clean-utility loss was zero percentage points.
- Injected-condition CER: A0 10/60 (16.7%); A1/A2/A3 0/60. The A0-minus-A3 paired 95% interval is [0.083, 0.267]. These ten A0 errors are not all attributable to injection: nine matched pairs also failed clean; one failed only when injected.
- Praxis report: **complete**, with Markdown, DOCX, PDF, six tables and two figures. All **21 rendered pages** passed visual review; receipt: `paper/RENDER_QA.md`.

`FINAL_DETERMINATION.md` preserves the unchanged decision rule; `paper/PRAXIS_REPORT.md` presents the five-chapter report, bounded interpretation, provenance and reproduction instructions. `REPRODUCIBILITY.md` provides exact commands. Pilot and fixture evidence remain separate from discovery. This is a one-model result on inert symbolic security workflows; cross-model replication remains untested.
