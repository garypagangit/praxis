## Retrospective sensitivity to captures, fitting seeds and repeated aggregates

A prespecified retrospective audit retained all 36 paired comparisons and exhaustively omitted each capture while holding predictions fixed. It also omitted each fitting seed within all 12 groups, averaging the remaining per-seed metrics rather than pooling flows. The fixed four-class schema and undefined-support rule were preserved. These are finite sensitivity calculations, not refits, confidence intervals or independent replications.

Macro-F1 changes in the table are score points (raw score differences multiplied by 100); warning-recall changes are percentage points.

| Omitted unit | Clean B3 Δ macro-F1 (×100) | Δ exfil warning pp | Mean extra exfil → benign | Mean extra benign alerts |
| --- | --- | --- | --- | --- |
| None (three-seed mean) | 2.31 | -8.93 | 307.33 | 11.00 |
| Fit seed 8101 | 0.65 | -0.36 | 12.50 | 14.00 |
| Fit seed 8102 | 3.51 | -13.35 | 459.50 | 3.00 |
| Fit seed 8103 | 2.78 | -13.07 | 450.00 | 16.00 |
| Capture 6 (three-seed mean) | 1.57 | -25.71 | 305.67 | 7.00 |
| Capture 7 (three-seed mean) | 3.67 | -8.95 | 307.33 | 8.67 |
| Capture 8 (three-seed mean) | 2.26 | -9.12 | 293.00 | 7.67 |
| Capture 9 (three-seed mean) | 2.16 | -7.74 | 246.33 | 9.67 |
| Capture 10 (three-seed mean) | 1.52 | -2.80 | 77.00 | 11.00 |

Across the 12 mean comparisons, 9 show higher F1 with fewer exfiltration warnings on all data; 9 preserve that direction under every fitting-seed omission and 9 under every capture omission. The full set includes temporal-access comparisons where both scores and warnings improve, and conditions with opposite or zero changes.

The 27 registered PX081 contrasts include 24 distinct ordered capture-confusion signatures. The F1-up/warning-down count is 19/27 registered pairs or 17/24 aggregate-equivalent signature classes. Neither denominator counts independent experiments. Equal confusion signatures do not prove that the individual predictions match; they identify repeated sufficient statistics for the reported metrics.

All 180 capture omissions, 36 seed omissions, supports, nulls and full group ranges are retained in the accompanying sensitivity evidence package. This audit remains retrospective on one exposed campaign. The original interval and scope qualifications therefore continue to apply.
