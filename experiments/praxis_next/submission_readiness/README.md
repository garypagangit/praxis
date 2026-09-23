# Praxis review package

**When Better APT Scores Hide Missed Attack Warnings**
Completed reviewer preparation: September 23, 2026.

## Start here

1. Read the [review edition PDF](apt_praxis_review_edition.pdf), or edit the [Word manuscript](apt_praxis_review_edition.docx).
2. Use the [short defense brief](praxis_defense_brief.pdf) to explain the contribution and its limits.
3. Give a reviewer the [complete review bundle](praxis_review_bundle.zip). It contains the original study, the original evidence ZIP, all added sensitivity results, public verification code, and the new review documents.
4. Use the [prepared adviser message and decision record](ADVISER_HANDOFF.md) for substantive human review. It has not been sent, and no approval or submission is recorded.

The review edition preserves the completed manuscript and adds Appendix D. The original study files and 206 manifest bindings remain unchanged. The [Markdown paper](praxis_review_edition.md) is the editable source. The manuscript is complete for review; institutional formatting, author affiliation and adviser/venue acceptance require the researcher's actual details and decisions.

## What the next-step work established

| Check | Actual outcome | Meaning |
|---|---|---|
| Exhaustive fixed-prediction sensitivity | 180 capture omissions; 36 seed omissions; 3,816 scalar cross-checks passed | All nine mean comparisons with F1 up and exfiltration warning recall down retain that direction under every specified single-capture and single-seed omission. |
| Headline magnitude | Clean budget-three loss is 8.93 percentage points across three seeds, 0.36 after seed 8101 is omitted | The direction survives, but the magnitude is strongly seed-sensitive. |
| Temporal comparison | Current-feature time-mixed minus past-only F1 stays positive in 15/15 seed/capture omissions | The observed protocol effect is not removed by any one capture deletion. |
| Repeated aggregates | 27 acquisition comparisons contain 24 ordered confusion signatures; directional count 19/27 or 17/24 signatures | Neither denominator measures independent replications. |
| Fresh local environment | 36 comparisons and 720 interval calculations reproduced; all 206 original hashes matched | Public arithmetic is reproducible without private prediction files. This is not an independent laboratory's replication. |
| Delivery repair | Added the unchanged original ZIP beside its extracted contents; all 74 original local links passed | One missing archive link was repaired without changing any original scientific file. |
| New-source qualification | Neither checked Sandworm nor CAM-LDS release currently supports the unchanged complete warning/workload replication | The specific source limits and concrete next intake are documented. No additional classifier result is claimed. |

All results remain from the originally exposed campaign and completed predictions. No new models, GPUs, or AWS resources were used for this extension. There is no new compute spend.

## Evidence and verification

- [Sensitivity protocol, full results and interpretation](sensitivity/REPORT.md), frozen before omission calculations in commit `e9de91d`.
- [Sensitivity arithmetic receipt](sensitivity/AUDIT.json) and [publication bindings](sensitivity/PUBLICATION.json).
- [Fresh-environment report](clean_room/REPORT.md), including the original packaging failure and the repaired pass.
- [Next replication source decision](NEXT_REPLICATION_SOURCE.md) and [captured source metadata](NEXT_REPLICATION_SOURCE_METADATA.json).
- [Bounded same-team claim review](REVIEWER_CLAIM_CHECK.md), which is a computational review, not external peer review.
- [Document rendering and visual-review receipt](DOCUMENT_RECEIPT.json).
- [Review file manifest](REVIEW_MANIFEST.json).

`REVIEW_BUNDLE_RECEIPT.json` and `REVIEW_EXTRACT_VERIFICATION.json` accompany the distributed ZIP in Git. They are external attestations, excluded from the archive they attest to. The ZIP does not include itself. The original evidence ZIP is an unchanged, separately named historical artifact within the new bundle.

## Reproduce from the review bundle

Extract `praxis_review_bundle.zip` into a new directory and use that extracted directory as the working directory. Create a fresh Python 3.11 environment, install NumPy 2.2.6, and run:

```powershell
python -I -B experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis/verify_public.py --receipt C:/path/to/new-results/PUBLIC_VERIFICATION.json
python -I -B experiments/praxis_next/measurement_praxis/verify_package.py --receipt C:/path/to/new-results/PACKAGE_VERIFICATION.json
```

Create the new result directory first; choose a path outside the extracted evidence to preserve the delivered receipts. Both verifiers use public files. They check aggregate calculations, source bindings and recorded render status; they cannot recreate private row-level predictions, establish author-label correctness or repeat model fitting without the qualified source inputs.

The new sensitivity source and all public inputs are included. Its runner intentionally refuses to overwrite recorded outputs and checks the original freeze through Git. To repeat it, use a separate checkout of commit `e9de91d`, which contains the frozen source and inputs before omission outputs were created; do not erase the archived results. From that separate checkout, run `python experiments/praxis_next/submission_readiness/sensitivity/run.py run --commit e9de91d`. Its five synthetic tests can also be run from the repository without altering study artifacts:

```powershell
python -m unittest experiments.praxis_next.submission_readiness.sensitivity.test_sensitivity
```

The original [reproduction guide](../measurement_praxis/REPRODUCE.md) specifies private-input and original model-fitting requirements. The [bundle builder](build_review_bundle.py) and [document builder](build_review_documents.py) record the delivery process. The document builder uses python-docx, PyMuPDF, Pillow and LibreOffice; rendering is separate from scientific calculation.

## What is next for the researcher

The paper, evidence and review materials are ready to assess. The prepared handoff asks the adviser to decide whether this bounded measurement contribution fits the praxis and whether independent-execution replication is required for the intended institution or venue. Author information, required format and any disclosure language can then be applied to the editable manuscript. Those human decisions have not been simulated.
