# Praxis 06 Target Style Decision

Generated: 2026-05-14

## Decision

Default target style: **thesis chapter first, venue conversion second**.

Reason: the current evidence package is already defense-ready and bounded. A thesis/Praxis chapter can preserve the full audit trail, negative DAPT boundary, seven-seed addendum, and claims-not-made guard without forcing premature page-limit compression. After committee review, the same source can be compressed into an arXiv, ACSAC/RAID-style, IEEE, or ACM venue format.

## Current Source

Primary LaTeX source:

- `paper/praxis06_tta/main.tex`
- `paper/praxis06_tta/thesis_chapter.tex`

Latest confirmed build:

- GitHub Actions run: `25875430166`
- Commit: `ecfb6e0`
- Artifact: `praxis06-tta-paper`
- PDF: `8` pages, figure-integrated

## Claim Guard

Keep these unchanged during thesis/venue conversion:

| Item | Guard |
|---|---|
| Primary result | Original locked three-seed replay remains primary. |
| Robustness result | Seven-seed run is a defense addendum, not a replacement. |
| Thresholds | No new threshold search. |
| PR-AUC framing | Decision-policy improvement, not representation/ranking improvement. |
| DAPT2020 | Detector-recipe appendix and negative TTA boundary only. |
| Provenance | Label-blocked architecture track, not a positive detector claim. |

## Recommended Thesis Chapter Shape

1. Introduction and problem motivation.
2. Research questions and hypotheses.
3. Related work.
4. Dataset, split, leakage controls, and EDA.
5. Method: frozen detector, BatchNorm adaptation, selective gate, locked replay.
6. Graphical model representation.
7. Results: locked replay, per-seed table, confidence-reject baseline.
8. Defense hardening: seven-seed addendum, validation sensitivity, stronger frozen baselines, BN order, override decomposition.
9. External validity: DAPT2020 recipe transfer and negative TTA gate.
10. Threats to validity and claims not made.
11. Conclusion.

## Venue Conversion Notes

| Target | Fit | Conversion note |
|---|---|---|
| Thesis/Praxis chapter | Best immediate fit | Keep appendices and audit details visible. |
| arXiv preprint | Strong fit | Keep current article style, add author/affiliation, expand related work slightly. |
| RAID/ACSAC-style paper | Good later fit | Compress appendices and move artifacts to supplementary material. |
| IEEE/ACM format | Plausible later fit | Replace class, shrink tables, keep only one PR figure in main text. |
| USENIX Security mainline | Stretch | Would need stronger mechanism or second positive dataset; do not overfit for this now. |

## Next Editorial Step

Confirm the thesis wrapper compiles, then do a full-size PDF read for phrasing, figure placement, and table readability. Create a venue-specific branch only after the committee/thesis chapter package is stable.
