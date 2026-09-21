# Fixed-window data qualification

Status: exploratory retrospective T1105 manifestation-window diagnostic.

Every complete 10-second UTC bin is pooled across all acquired defender audit hosts. Empty bins remain. Positive means any overlap with an author T1105 window; other annotated periods are negatives. Unannotated bins are unknown: they consume the full-grid review budget but are excluded from conditional classification metrics and are not false positives. Mixed bins remain positive and are counted separately.

**The existing replay slice is annotation-derived.** Fixed bin boundaries are label-independent within `[first author start - 120 seconds, last author end)`, but this is not a whole-day or annotation-independent acquisition cohort. Partial boundary bins are excluded. Predictions are made at window close; this is not an early-warning test.

| Split | All bins | Positive | Other-label negative | Unknown | Empty positive | Mixed positive | Source target windows covered |
|---|---:|---:|---:|---:|---:|---:|---:|
| fit | 1610 | 146 | 1047 | 417 | 13 | 0 | 35/35 |
| development | 227 | 9 | 155 | 63 | 0 | 0 | 5/5 |
| calibration | 79 | 3 | 45 | 31 | 0 | 0 | 1/1 |
| test | 3564 | 106 | 3072 | 386 | 0 | 0 | 42/42 |

The split names above record the original source allocation. The new diagnostic uses all five previously exposed families in leave-one-family-out development evaluation; these old role names do not designate a fresh test or calibration split.

## Interpretation limits

- Author manifestation windows include padding, manual shifts, and sleep extensions; window membership is still weak supervision, not exact malicious activity.
- Negatives are other annotated technique periods, not independently verified benign periods. Unknown windows remain in ranked review and are counted separately from known-label metrics.
- Any-overlap labeling can mix target and other stages and dilute short target evidence across a whole ten-second bin.
- All defender audit hosts are pooled, matching the scope of global source labels but still including unrelated/idle activity; no ground truth of the affected host is inferred.
- Only audit records are present; deleting EXECVE and PROCTITLE does not remove all command/program evidence from SYSCALL, PATH, and other surviving fields.
- Lexical paths, program names, channel counts, volume, and coarse identity classes may encode simulation-family artifacts despite fixed host/run/technique masking.
- Some generic TECHNIQUE_MARKER/SCENARIO_MARKER/CHALLENGE_MARKER tokens may encode testbed artifacts; exclude these literal markers from model text.
- Five scenario families with correlated variants, including one family with only one target source interval, cannot establish general APT detection or reliable population uncertainty.
- Prior outcomes on this cohort are exposed: every new result is development evidence and needs fresh external confirmation.
- No fits, tuning, labels created by a model, or human audit were performed by this qualification.

Detailed aggregate counts by family and run, source hashes, boundary exclusions, source coverage, and command-removal support are recorded in [DATA_QUALIFICATION.json](DATA_QUALIFICATION.json). No raw attacker command logs or event text are included.
