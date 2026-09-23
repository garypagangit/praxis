# When Better APT Scores Hide Missed Attack Warnings

**Completed empirical praxis manuscript and evidence package - September 23, 2026.**

[Word paper](apt_evaluation_praxis.docx) | [PDF paper](apt_evaluation_praxis.pdf) | [Evidence index](EVIDENCE_INDEX.md) | [Complete public evidence ZIP](apt_evaluation_praxis_evidence.zip)

## What the paper establishes

1. **Training composition changes reported stage performance.** With the same model, anchor rows and class budgets, time-mixed fitting raises macro-F1 by .0632 and movement-label recall by 35.19 percentage points in the current-feature comparison.
2. **A better headline score can hide lost attack warnings.** Across all 27 declared acquisition seed/condition/budget comparisons, 19 show higher macro-F1 with lower exfiltration warning recall. These are dependent comparisons on one campaign. The clean largest-budget mean warning loss is 8.93 percentage points, with additional misses of 897, 3 and 22 across seeds; the paper exposes that variation.
3. **History produces useful chronological gains with a smaller warning tradeoff.** Macro-F1 improves .7365 to .7582 and mean benign alerts decrease 24.0 to 14.3; exfiltration-to-benign predictions increase by 7, 6 and 8 among 1,722 anchor exfiltration rows.
4. **Dataset eligibility is itself measurable.** An independent source-count sweep confirms no all-stage DAPT cutoff across 28,941 distinct timestamp states. SCVIC has recorded-time support but unresolved physical chronology. DSRL derives from DAPT, and no qualified S-DAPT release was acquired.

The contribution is controlled evidence and an executable audit using established metrics. Main model evidence remains one exposed UNRAVELED campaign. The four-source extension is a completed qualification study, not four new fitted replications.

## Finished deliverables

- Full manuscript: 24 pages, 18 source references, 14 tables and three figures.
- [Complete 36-pair retrospective reanalysis](evidence/paired_reanalysis/REPORT.md), all stage outcomes, per-seed conditional intervals and public aggregate data.
- [Public-only arithmetic verifier](evidence/paired_reanalysis/PUBLIC_VERIFIER.md), reconstructing the reported metrics without private flow records.
- [Independent dataset verification](evidence/qualification_audit/REPORT.md), all native counts and source checks.
- [Scientific review](SCIENTIFIC_REVIEW.md), [reproduction instructions](REPRODUCE.md), [researcher review checklist](REVIEW_CHECKLIST.md).
- [Final verification](FINAL_VERIFICATION.json) and [artifact manifest](PACKAGE_MANIFEST.json).

This completion fitted zero new models and incurred $0 new AWS spending. It analyzes the unchanged completed experiments and supplies a complete paper on their bounded findings. Institutional front matter, researcher authorship and an actual submission remain researcher-owned administrative steps; no committee approval or external submission is claimed.
