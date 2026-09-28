# Integrated final praxis and GWU defense

Gary Pagan — September 28, 2026

**153-page paper; 25 main defense slides plus 12 technical backups.** Campaign validation is incorporated throughout this complete edition.

- [Word paper](delivery/Gary_Pagan_Final_Praxis.docx) · [PDF paper](delivery/Gary_Pagan_Final_Praxis.pdf)
- [PowerPoint defense](delivery/Gary_Pagan_GWU_Praxis_Defense.pptx) · [PDF slides](delivery/Gary_Pagan_GWU_Praxis_Defense.pdf)
- [Speaker notes](delivery/Defense_Speaker_Notes.txt)
- [Source manuscript](manuscript.md)
- [Dated release and downloadable evidence](https://github.com/garypagangit/praxis/releases/tag/praxis-integrated-20260928)
- [Evidence hashes and download URLs](delivery/EVIDENCE_INDEX.json)

## What changed

The integrated paper adds AIT source literature, Section 3.12 methods, Section 4.11 results and Appendix E complete per-seed outcomes, and updates the abstract, scope, discussion and conclusions. Main slides 19–21 present the AIT evaluation; limits and conclusions follow in slides 22–25. Technical backups and speaker notes are updated.

All 3,465,342 AIT source rows were examined. Six executions supplied 2,397,158 eligible training rows; two later executions supplied 1,067,211 evaluation rows. All 1,245 computational audit checks passed.

The original error-focused versus entropy higher-F1/lower-warning direction did **not** recur in any of six execution-by-seed comparisons. Wilson showed a small opposite-order tradeoff; Harrison improved both outcomes under entropy. This is an adapted three-class, history-only evaluation. Exact four-class replication, unrelated-campaign generalization and operational benefit remain unresolved.

## Reproduction and tracking

The dated release includes the integrated review package and the original/full-release and AIT reproduction bundles. Large archives are release assets; manuscript sources, documents, aggregate evidence and build code are versioned in Git.

- [AIT protocol, code and audit](../campaign_validation_20260928/evidence/)
- [Full-release UNRAVELED code and audit](../gwu_final_20260927/full_release/)
- [Integration code and QA](integration/)

Reproduction scripts retain recorded workstation paths. Adjust these when extracting on another machine and record the amendments. The supplied build scripts require their recorded Python dependencies and, for slides, artifact-tool. Computational checks do not represent committee approval.

The local delivery manifest preserves the original delivered files' hashes. EVIDENCE_INDEX.json here additionally supplies release download URLs.

## Downloading full reproduction archives

The two large reproduction ZIPs are distributed as 64 MiB parts because whole-file uploads timed out. Download all `.part` files, `REPRODUCTION_PARTS.json` and `reassemble_evidence.py` into one folder, then run `python reassemble_evidence.py`. The script verifies every part and the reconstructed ZIP against SHA256. The review ZIPs can be downloaded directly.
