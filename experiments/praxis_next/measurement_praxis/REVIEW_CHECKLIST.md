# Manuscript review checklist

Use this as a review aid. It is not an approval record or a substituted human annotation audit.

| Review question | Evidence or manuscript section |
|---|---|
| Is there a concrete applied problem? | Sections 1 and 6: selecting a higher-scoring model can reduce attack warnings |
| What was actually contributed? | Controlled measurements, error-destination accounting and benchmark qualification; Sections 1.3 and 8 |
| How does it differ from close work? | Section 2 and LITERATURE_AND_CLAIMS.md; Uddin, TESSERACT, Bilot, Guerra, TAN-IDS and Othman are explicitly distinguished |
| Are the positive observations clear? | Sections 5.1-5.3: .0632 temporal F1 effect, warning/F1 mismatch, chronological history gains |
| Are unfavorable and unchanged observations retained? | Section 5, complete paired CSV, original seven-arm and budget tables |
| Is the warning-loss finding retrospective? | Abstract and Sections 3.1, 4.4, 7.3; preserved throughout |
| Are the rows and resampling units explicit? | Sections 3 and 4.4; five captures from one campaign; fitting seeds are not independent incidents |
| Are uncertainty and rare-class omissions visible? | Per-seed tables; 1,981/2,000 valid macro/movement bootstrap draws; source-group support counts |
| Can a reviewer recompute without raw traces? | Public capture confusion matrices, shared draws and independent public-only verifier |
| Does source qualification have an independent check? | Separate CSV-parser/timestamp sweep: 16 verification checks and 6 synthetic tests |
| Is dataset breadth stated accurately? | Four-source qualification, not four-dataset model replication; DSRL dependency and S-DAPT access limits |
| Does the paper avoid early-warning/theft claims? | Decision-time and target-semantics limits in Sections 3 and 7 |
| Is the final document readable? | Word/PDF render receipt and full-page visual review |

## Researcher-owned submission details

Before an actual school or venue submission, the researcher supplies their author name, affiliation, adviser/committee fields, required institutional template and any required AI-assistance disclosure. The manuscript does not fabricate these details. The empirical paper and evidence package are complete for substantive review; no external submission or correspondence was performed.

## Expansion priorities, separate from this completed paper

1. Independent repeated attack executions with trusted clocks and stage semantics.
2. SCVIC author-supported clock and row-to-execution mapping, or a qualified holdout.
3. A separately registered asymmetric-loss or warning-preserving decision policy, compared at measured workload.

These are extensions to the bounded findings, not prerequisites for reporting the completed study accurately.
