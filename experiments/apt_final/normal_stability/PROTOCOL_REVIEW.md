# Independent review: bounded normal-stability diagnostic

**Review date:** September 20, 2026. **Status:** design review, not the operative registration. `PROTOCOL.md` and `config.json` govern execution. No new experiment was run for this review; preceding frozen artifacts remain unchanged.

## Recommendation

Proceed with the proposed three-strategy comparison as a finite development study. Its question is whether normal-reference coverage and calibration account for the observed instability. It can close this specific candidate with a measured go/no-go decision; it cannot establish that all graph methods succeed or fail, or establish methodological novelty.

The must-have simple control is local-feature kNN with the same bank rows and observed inputs. Include the clean-bank/pooled-calibration arm to separate calibration changes from additional reference coverage. A new checker is unnecessary to answer this question.

## Controls that must be explicit before execution

1. **Four fixed whole-file roles.** For folds A/B/C/D, use fit pairs (0,1)/(1,2)/(2,3)/(3,0), calibration graphs 2/3/0/1, and validation graphs 3/0/1/2. Retrain each MLP/GIN encoder from scratch on its two fit graphs for the fixed ten epochs. Reusing the old three-graph encoder would expose validation data. Two versus three fit graphs changes the training regime, so comparisons with earlier studies are descriptive; within-study strategy comparisons isolate the reference/calibration intervention.

2. **Clean encoder training held constant.** Unless the operative protocol explicitly states otherwise, masks augment the reference bank and calibration views, not encoder training. All three strategies share each trained encoder. Recompute node features and graph embeddings after relationship removal, retaining full observed message-passing context. Neither MLP nor local features are immune to edge loss: their relation counts also change.

3. **Separate randomness.** Cross encoder seeds 101/211/307 with three fixed bank seeds independent of encoder seed. Masks must be fixed independently of both and shared across compared methods; record each graph's mask hash. This provides 36 fold/encoder/bank combinations per learned representation and dataset, not 36 independent campaigns. Local features do not depend on encoder seed: there are only 12 unique fold/bank combinations per dataset. Repeated copies must not increase their evidence weight.

4. **One reference budget.** Each strategy uses at most 8,192 reference rows and k=10, with shared sampling provenance across representations. Define pooled sampling precisely before running: a 50:50 clean/masked allocation is preferable to accidentally doubling the budget. Record graph, original row, and view for every bank entry, preserving legitimate duplicate-vector multiplicities. Sampling the same root row twice in different views must be documented. Bank-only standardization, its floor, and tie handling stay fixed. Pooling can also change scale estimates; its effect is the whole reference procedure, not an isolated proof of improved geometric coverage.

5. **Three fixed strategies.** Compare (a) clean bank/clean calibration, (b) clean bank/pooled clean-and-50%-masked calibration, and (c) pooled clean-and-masked bank/pooled calibration. Both pooled calibration views must have equal weight. Repeated views of one entity are dependent observations; stacking them does not create twice as many independent calibration entities. An empirical 1% pooled tail does not guarantee 1% false positives separately for clean and masked cases. Measure both explicitly.

6. **Freeze before attack replay.** Fit banks and calibration independently of normal-validation outcomes. Normal validation may be computed during the normal phase without adaptive decisions; then globally hash all normal fits, calibration, and results before accessing test0 annotations. Keep alpha=0.01 and the conservative tail/tie rule fixed. Do not pick a best seed, fold, k, bank, or strategy from validation outcomes or attack labels. Save numeric scores, decisions, fit-row provenance, and fixed masks so an independent auditor can reconstruct metrics and verify that validation rows never enter the corresponding bank.

## Finite decision rule

Report every representation/strategy with the same denominators and an explicit all-repeat gate, plus means and worst cases. Normal validation uses the upstream filtered-benign assumption; its meaningful primary outcome is false-positive rate, not recall or F1.

- **Normal-stability requirement:** held-out normal FPR <=2% for every fold, encoder/bank repeat, and both clean and 50%-masked conditions.
- **Detector requirement:** test0 annotated-malicious-entity recall >=50% and annotated-negative FPR <=2% for every repeat and condition. These bounds remain the existing engineering thresholds; applying them to the stress condition extends the screen prospectively rather than revising earlier results.
- **Earlier scoring-improvement requirement remains separate:** preserve the prior mean clean F1 improvement of at least 0.05 above the earlier best fixed comparator wherever the operative protocol carries that gate forward. Do not silently replace it with the new normal-only gate.
- **General result:** the same representation/strategy must pass on both datasets to support a two-dataset development claim. A dataset-specific pass stays dataset-specific. Passing the clean baseline alone supports detector feasibility, not a benefit from augmentation; report paired augmentation-versus-clean changes separately.

If no arm passes the full screen, close this reference/calibration candidate as **no-go under the tested procedure**. Identify whether failure is normal instability, insufficient malicious-entity recall, or both. Do not add a post-result checker or relax cutoffs. If a complete valid run is prevented by runtime or provenance failure, report incomplete evidence rather than scientific no-go.

## Conditional checker and scope limits

**Recommended ending: omit a conditional checker from this run.** The three controls can answer whether basic pooling works. If a conditional arm is retained, its exact observable inputs, fitting rule, minimum calibration support, fallback, and benign-only eligibility criterion must be registered before any results are inspected; run it only under that fixed rule. "Normal data justifies it" is too open-ended by itself. No simulator drop rate, intact-query counts, or missing-edge identities may be inputs. The prior low-degree selector failure rules out treating raw degree as an established measure of collection quality.

Source UUIDs, timestamps, and campaign boundaries are absent. Whole-file exclusion prevents direct reuse within a fold but cannot establish entity, temporal, host, or campaign independence. The four folds overlap in training data, and test0 is replayed throughout; confidence intervals treating these repeats as independent evidence are inappropriate. Test negatives may contain incompletely annotated activity. Conclusions concern annotated entities in these static prepared graphs, not APT actor identification or operational deployment.

Recent primary literature already covers [graph calibration under structural changes](https://proceedings.iclr.cc/paper_files/paper/2024/file/f3024ea88cec9f45a411cf4d51ab649c-Paper-Conference.pdf), [adaptive graph augmentation with conformal scoring](https://doi.org/10.1145/3696410.3714879), [mask-conditional calibration](https://proceedings.mlr.press/v300/fan26a.html), and [gating-based calibration similarity](https://proceedings.iclr.cc/paper_files/paper/2026/hash/97c8a8eb0e5231d107d0da51b79e09cb-Abstract-Conference.html). These motivate controls, not a novelty claim or a transferable coverage guarantee. A practical pass would justify further research; it would not by itself make a final novel praxis contribution.
