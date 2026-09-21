# Independent review before fixed-window model fitting

## Recommendation

Proceed with one bounded CAM-LDS T1105 diagnostic. The primary question is whether pooling a complete fixed window reveals useful evidence that an individual event misses. Pooled logistic regression is the primary model; ExtraTrees is a declared secondary control and cannot replace the primary after inspecting outcomes. The five scenario families have previously been exposed, so every outcome remains development evidence.

This review was performed by a separate AI/code reviewer before the new model fits. It is not human adjudication of the source labels. It checked the prior source qualification, the negative robustness-v2 results, and the new protocol and implementation. An independent calculation audit follows model execution; passing that audit establishes calculation consistency, not the truth of the source labels or a positive scientific result.

## Evaluation unit and review budget

- Build all complete, absolute-UTC ten-second bins within the existing replay envelope, before label assignment. Preserve empty bins and unknown-label bins. Pool only the acquired defender audit records from within each bin; prediction occurs at its end.
- Positive means any half-open overlap with an author-designated T1105 manifestation interval. Other annotated intervals are target negatives, and unannotated bins remain unknown. These labels do not establish that every event in a positive bin is malicious.
- Rank all bins within each run and inspect `ceil(0.10 * number_of_bins)`. Ties use SHA256 of the fixed prefix and window ID. Zero-score bins still consume the frozen review budget.
- The primary metric pools target counts within each held-out family, then averages recall equally over five families. Expected random-budget family recall is `sum_run(positive_bins * ceil(0.10 * all_bins) / all_bins) / family_positive_bins`.
- Report unknown selections separately. Confirmed-positive yield is a lower bound; unknown selections must not be called false positives. Known-bin AP, ROC-AUC, and known-only budget precision/recall/F1 are conditional secondary results.
- Remove EXECVE and PROCTITLE fragments without changing the roster or labels. Select the first-event control before removal and do not replace an event that becomes invisible.

## Frozen decision gates

These cutoffs are practical, descriptive development decisions chosen before fitting. They are not literature-derived success guarantees, statistical significance tests, or population assurances. The gates answer separate questions and must not be collapsed into a favorable aggregate result.

| Decision | Frozen criterion |
|---|---|
| Useful clean signal | Primary pooled-LR macro-family recall at least 0.40, at least three times macro expected random-budget recall, and above chance in at least four of five families |
| Pooling benefit | Pooled-LR clean recall exceeds first-event LR by at least 0.10 macro; positive differences in at least three families; no family difference below -0.10 |
| Added ML value over lexical rule | Pooled-LR clean macro recall exceeds the frozen transfer-tool rule by at least 0.05 |
| Command-record loss gap | Primary clean macro recall minus command-absent macro recall is at least 0.10 |

The activity-count ranking is an additional no-fit shortcut control. A strong rule or activity-count result can establish predictable source-window structure without establishing a benefit from added model complexity. An ExtraTrees-only success is a secondary lead requiring a new frozen follow-up; it cannot convert primary failure into primary success.

If the useful clean-signal gate fails, retire the primary pooled-LR formulation under this design. If useful clean signal passes and a command-record loss gap exists, qualify surviving additional sources before proposing a recovery experiment. If useful clean signal passes without a large loss gap, this stress has not demonstrated a need for that recovery mechanism. No outcome here validates a novel method.

## Required integrity checks

1. Verify source, annotation, feature-cache, protocol, and code hashes before fitting. Preserve a pre-fit receipt. Reject a protocol/cache mismatch rather than silently accepting new features.
2. Verify both classes in every training fold, disjoint held-out families, and stable ordered training/test window IDs. Train only on clean, known-label bins in the other families.
3. Freeze the transfer-tool vocabulary and model settings before examining new scores. Exclude source labels, interval IDs, scenario/host names, absolute time, bin indices, and literal annotation-mask marker tokens from lexical features.
4. Report positive source-interval coverage, boundary exclusions, empty positive bins, overlap fractions, and actual rounded review budgets. Recompute scores' selection masks and metrics independently after execution.

## Limits that remain after pooling

The selected replay envelope itself comes from author annotation boundaries; this is not continuous whole-day monitoring. The source windows contain padding, manual shifts, and sleep extensions, and there is no ordinary-user benign workload. Pooling aligns the scope of observations with the global labels but does not repair their maliciousness truth. Known negatives are other technique periods. Source counts, generic paths, and program names can still encode simulation artifacts. Family 4 contains only one T1105 source episode; correlated variants are not independent campaigns. Command removal retains program and command clues in other audit fields and is not a whole-sensor outage. The experiment cannot establish early warning, actor attribution, operational false-alert rates, broad APT detection, or fresh independent confirmation.

The strongest defensible positive outcome is a developmental finding about evidence aggregation or remaining signal under this controlled stress. A praxis contribution still needs a specific mechanism, comparison against close literature, and new confirmation evidence.
