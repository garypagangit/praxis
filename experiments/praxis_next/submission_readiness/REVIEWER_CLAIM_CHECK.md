# Reviewer claim check: sensitivity analysis and defense brief

**Review date:** September 23, 2026
**Scope:** Independent read-only scientific/editorial check by a separate agent in the same project team.
**Result:** **Numerical and substantive claim checks PASS.** All requested wording corrections are resolved. The final Appendix D pages also pass the bounded visual check described below.

## Materials and method

Reviewed `sensitivity/PAPER_DATA.json`, `PAPER_SECTION.md`, `PAPER_DETAILS.json`, `SUMMARY.json`, the complete omission tables, aggregate-equivalence inventory, analysis plan/freeze, and `DEFENSE_BRIEF.template.md`. Used the original published per-capture confusion counts and comparison identities from `measurement_praxis/evidence/paired_reanalysis/`.

A separate temporary, read-only Python calculation imported no project analysis modules. It used direct confusion-matrix formulas to recompute all full-population points and all **180 capture omissions**, then independently averaged the retained fits for all **36 seed omissions** and all **12 group means**. It checked **4,770 scalar values**, temporal omission extrema/signs, and the aggregate-equivalence inventory. Every checked value matched within an absolute tolerance of `1e-12`. No model fitting, threshold choice, new literature search, or frozen-file modification occurred.

This is a calculation and interpretation check. It does not validate source labels, establish new campaigns, or substitute for an external scholarly review.

## Checked claims

| Claim in the proposed prose | Check and conclusion |
|---|---|
| 180 capture omissions and 36 seed-omission means cover the complete registered comparison inventory | Confirmed: 36 pairs × five captures; 12 groups × three fitting seeds. No favorable subgroup replaces the full inventory. |
| Clean budget-three mean has higher F1 and lower exfiltration warning recall under every single capture/seed omission | Confirmed for all five capture-omission means and all three seed-omission means. These are separate one-unit deletions, not all combinations of deletions. |
| Excluding seed 8101 changes warning loss from 8.93 to 0.36 percentage points and extra missed warnings from 307.33 to 12.50 | Confirmed. The retained mean F1 difference is +0.0064827, or +0.65 score points on the ×100 scale. This supports seed sensitivity of the magnitude. |
| Clean budget-three individual fitting seeds yield 10 of 15 capture-omission reversals | Confirmed: five for seed 8101, zero for 8102, five for 8103. Mean-direction stability must not be described as identical per-seed behavior. |
| Nine of twelve full group means retain the reversal under every specified single-seed and single-capture omission | Confirmed. The group means and directions are descriptive; the groups share observations and fitted components. |
| Current-feature and history-feature mixed-minus-past F1 remain positive in all 15 seed/capture-omission pairs each | Confirmed, including the per-seed extrema in `PAPER_DETAILS.json`. |
| Chronological history-minus-current F1 is positive in 14 of 15 omission pairs | Confirmed. Omitting capture 9 in seed 20260924 gives −0.00134983, or −0.13 score points. All three-seed means remain positive. |
| No capture omission produces unsupported evaluation-class metrics | Confirmed for these one-capture deletions. This is compatible with unsupported earlier bootstrap draws: replacement sampling can omit several distinct captures. |
| The 27 acquisition contrasts contain 24 distinct ordered per-capture confusion signatures; reversal counts are 19/27 or 17/24 | Confirmed by independently grouping the ordered confusion payloads. The three repeated classes pair clean and wrong-host budget-one conditions within each seed. This is aggregate equivalence, not independence or proof of identical row predictions. |
| The defense brief's three original headline findings remain correct | Confirmed against the old public outputs. The sensitivity analysis does not revise those original point estimates. |

## Presentation corrections and assembled-document recheck

1. **F1 units — resolved:** Updated `PAPER_DATA.json`, `PAPER_SECTION.md`, and review-edition Appendix D use **F1 difference ×100** or **score points**, retaining **percentage points** for warning recall. The numerical details and summary hashes are unchanged.
2. **Class terminology — resolved:** Updated sensitivity prose and Appendix D say **declared evaluation class** or **the fixed four-class schema**. The grouped targets are no longer described as the complete source-native taxonomy.
3. **Generated defense brief - resolved:** The one unfavorable chronological-history omission now says **0.13 score points (0.0013 raw macro-F1)**. Appendix D also uses the correct score-point units.

The assembled `praxis_review_edition.md` Appendix D and `praxis_defense_brief.md` were then read. Their numerical and contribution claims match the checked sensitivity outputs. Both retain retrospective status, fixed predictions, seed sensitivity, dependent aggregate signatures, one exposed campaign, and no completed external review. All relative links resolve locally and neither document contains unexpanded template tokens.

The fresh-environment statements also match the clean-room receipts: 36 comparisons, 720 intervals, 66 public aggregate tables, 2,000 resampling draws, and 206 original artifact hashes. The original package's one missing link and subsequent 74-link pass remain disclosed. This was a fresh local Python environment with Python-level file-open checks, not an operating-system sandbox or an external laboratory's replication.

The source-intake wording is also resolved: it now says **no additional corpus archive download or fit**. Public metadata and the small Sandworm README were read, as the intake record documents; no new scientific result depends on that wording.

When excerpting the compact addition, retain the full report's explanation that capture deletion changes the evaluation population while predictions stay fixed. It is not model refitting or generalization to an unseen capture. Compact tables should be read with the detailed retained supports; for example, omitting capture 6 leaves 1,189 exfiltration rows rather than the original 3,442, so rate and count magnitudes change together.

## Does this change the praxis contribution?

**It strengthens the explanation of the measured finding, not its external validity.** The evidence now shows that the mean-direction example is not eliminated by any one specified capture deletion or one fitting-seed deletion. It also quantifies a substantial weakness of a single headline effect size: seed 8101 accounts for most of the clean budget-three mean lost-warning count.

The appropriate conclusion remains a controlled, reproducible measurement contribution using established metrics. Do not upgrade it to a consistently superior detector, a stable population effect size, an untouched confirmation, or evidence across independent campaigns. “Direction retained under the specified single-unit omissions” is supported; an unrestricted “robust result” would be too broad.

The defense template and its assembled version preserve this framing: they identify one previously examined campaign, author discovery labels, completed flows, existing metrics, dependent comparisons, and an outstanding human review decision. The two generated sections are now populated and were checked; neither version claims that adviser/committee approval has occurred.

## Final appendix visual check

Original-resolution rendered pages **25, 26, and 27** were inspected. Text, tables, headings, and page numbers are readable, with no material clipping or overlap. The normal whitespace at the end of page 27 is not a missing-content finding. The [visual receipt](REVIEW_APPENDIX_VISUAL.json) binds this inspection to the exact page images and final PDF. Pages 1-24 were not re-inspected in this check; the parent reviewer reports they are pixel-identical to the earlier reviewed edition. Defense-brief visual review was assigned to the parent reviewer.

## Reviewed evidence snapshot

| Artifact | SHA-256 |
|---|---|
| sensitivity/PAPER_DATA.json | b1f81776cc1910fed236fec5e5519c23eaf911415cc4fb03653530119a79140d |
| sensitivity/PAPER_SECTION.md | 71208edf5cfbc0032693ad5e08dfa86da550220d9fbaeb900250fd5451a911d3 |
| sensitivity/PAPER_DETAILS.json | b5ac25d5e797405af3f3b58109c7d73335df6e577099935306767e43eb075109 |
| sensitivity/SUMMARY.json | 06cecc2a08fc7f7032d8efeebaa96d3dea8334612be70d0cacbfa01749008b95 |
| praxis_review_edition.md | f7229bd0912991d80b19f373ce844f1c26b82f1167ddfe4fd9d9ec4983793a1e |
| praxis_defense_brief.md | cbc3be4a8b8abaf3a21bf27517bd150410cb4c2c2235cdaab00a495f20b229d1 |

The checked scientific claims are consistent with these artifacts. This bounded PASS is not a publication-acceptance or institution-specific readiness guarantee.
