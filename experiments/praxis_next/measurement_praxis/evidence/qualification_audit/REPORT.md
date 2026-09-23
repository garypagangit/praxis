# Independent verification of dataset qualification

**Completed September 23, 2026.** The direct recount and tied-timestamp sweep reproduced the existing D1 native counts and cutoff-support findings. All 16 registered checks passed; six verifier tests passed. This is a completed measurement result. It neither fits nor rejects an attack detector.

## Evidence and reproduction

- [VERIFICATION.json](VERIFICATION.json): actual CSV counts, source hashes, date counts, direct cutoff counts, and sweep results.
- [SOURCE_REVIEW.json](SOURCE_REVIEW.json): bounded primary-source access receipts and provenance findings.
- [NATIVE_CLASS_COUNTS.csv](NATIVE_CLASS_COUNTS.csv): publication-ready native-class counts, without merging different stage vocabularies.
- [verify_qualification.py](verify_qualification.py) and [test_verify_qualification.py](test_verify_qualification.py): source frozen at commit `e6b5799` before this execution.
- [MANIFEST.json](MANIFEST.json): hashes of the verification package. Raw CSVs remain private.

From the repository root, with access to the private files named in the receipt:

```powershell
python -m unittest experiments.praxis_next.measurement_praxis.evidence.qualification_audit.test_verify_qualification -v
python -m experiments.praxis_next.measurement_praxis.evidence.qualification_audit.verify_qualification --commit e6b5799
```

The execution finished at `2026-09-23T18:27:39.853230+00:00`. It used the Python standard-library CSV parser, explicit date formats, and counters; it imported none of the original support-bound implementation. Source hashes were checked before and after reads. The headerless DAPT Thursday-private file retained its first row using the verified reference schema in memory. Source bytes were not changed.

This is an independent implementation check by the same agent team, using previously exposed files. It is not an external blinded replication. No AWS computation or model fitting was performed.

## Actual native support

Counts describe original input rows before any model-specific predictor deduplication. Native labels remain distinct across datasets. DAPT benign capitalization is normalized from `BENIGN` to `Benign`; no attack labels are merged.

| Dataset | Native class | Rows |
|---|---|---:|
| SCVIC-APT-2021 | NormalTraffic | 254,836 |
| SCVIC-APT-2021 | InitialCompromise | 73 |
| SCVIC-APT-2021 | Reconnaissance | 833 |
| SCVIC-APT-2021 | Pivoting | 2,122 |
| SCVIC-APT-2021 | LateralMovement | 729 |
| SCVIC-APT-2021 | DataExfiltration | 527 |
| **SCVIC-APT-2021 total** | | **259,120** |
| DAPT2020 | Benign | 63,712 |
| DAPT2020 | Reconnaissance | 11,909 |
| DAPT2020 | Establish Foothold | 8,604 |
| DAPT2020 | Lateral Movement | 2,451 |
| DAPT2020 | Data Exfiltration | 15 |
| **DAPT2020 total** | | **86,691** |
| DSRL-APT-2023 | Benign | 10,000 |
| DSRL-APT-2023 | Reconnaissance | 14,366 |
| DSRL-APT-2023 | Establish Foothold | 22,968 |
| DSRL-APT-2023 | Lateral Movement | 12,664 |
| DSRL-APT-2023 | Data Exfiltration | 5,002 |
| **DSRL-APT-2023 total** | | **65,000** |
| S-DAPT-2026 | No acquired author data | **Unmeasured** |

The S-DAPT entry is unavailable evidence, not an observed zero attack count. DSRL's native stage counts are not uniformly balanced.

## Direct temporal-support check

The declared diagnostic requires at least **two earlier fitting rows and one later test row for every native class**. This is a minimal support condition chosen for this audit, not a literature-mandated performance threshold or evidence of statistical power. A row is earlier when its recorded start is strictly less than the cutoff. A start equal to the cutoff belongs to the later side.

The verifier independently groups equal recorded timestamps and sweeps every boundary between adjacent groups, maintaining actual per-class earlier/later counts. It does not call or reproduce the original max(second-earliest)/min(latest) calculation. Within each interval between adjacent timestamps, membership is constant. Exterior intervals cannot qualify because one side is empty. Ties remain intact; no classes, duplicates, or unfavorable dates are dropped.

| Dataset | Distinct tied-time blocks | Membership intervals checked | Feasible intervals | Recorded-start conclusion |
|---|---:|---:|---:|---|
| SCVIC-APT-2021 | 11,694 | 11,693 | 9,475 | Minimal row support possible in `(2015-10-21 10:21:12, 2015-10-21 22:56:16]` |
| DAPT2020 | 28,942 | 28,941 | 0 | No all-native-class single cutoff meets even this minimal condition |

### DAPT2020: separation of attack stages establishes the constraint

Every reconnaissance row starts before every exfiltration row: the latest reconnaissance is **July 17, 2019, 19:24:55**; the earliest exfiltration is **July 19, 2019, 16:31:47**. To include two exfiltration rows in earlier fitting, a cutoff must be later than **July 19, 16:38:37**. To retain any later reconnaissance row, it must be no later than **July 17, 19:24:55**. Both requirements cannot hold.

The direct sweep therefore confirms a constraint across all single cutoffs, rather than failure of only the earlier 60/15/10/15 allocation. Completed-flow availability would be stricter than the optimistic start-only calculation. This result does not preclude binary detection, unknown-stage studies, or separately scoped tasks; those would answer different questions. It also does not imply a model performs poorly.

### SCVIC: sufficient row counts do not validate the clock

The lower boundary is set by the second recorded DataExfiltration start; the upper boundary by the last LateralMovement start. At the lower boundary exactly, only one exfiltration row is earlier. Immediately after it, two are earlier. At the upper boundary, two movement rows remain later; immediately after it, none remain later.

These are recorded-start count findings only. The CSV contains **220 NormalTraffic rows dated January 17, 1970**, with its other **258,900 rows dated October 21, 2015**. Mixed minute/second precision, an unqualified physical clock and timezone, and missing execution identities remain unresolved. No date repair is made. The table must not be described as a valid deployment chronology, nor as evidence that every SCVIC cutoff fails.

## Source provenance and remaining gaps

| Dataset | Verified available artifact and scope | Unresolved requirement |
|---|---|---|
| SCVIC-APT-2021 | Local author-attributed training CSV: 128,590,331 bytes; SHA-256 `a67b7a24196fc8c9e3b15ec7cf7b48b6a62f316fe24fc05fd9067dc745b3cf6e`. Current DataCite metadata identifies CC-BY-4.0. | No author checksum comparison, clock explanation, row-to-execution map, or acquired author test CSV. |
| DAPT2020 | Ten private/public-network flow CSVs with native Stage and Activity annotations; all source hashes are in the receipt. Author documentation defines Timestamp as flow start. | No independent repeated-campaign identities or qualified author holdout; duration/availability semantics and redistribution license not qualified here. |
| DSRL-APT-2023 | Author CSV and metadata pinned to `31bd0987bf84a4616fc9f9a60410a704a0ce4967`; all four artifact hashes match; repository LICENSE has the MIT header. | Synthetic attack chronology and dependence on DAPT2020 prevent treatment as independent real-data replication. No independent generator realization or author holdout qualified. |
| S-DAPT-2026 | Current manuscript/release status reviewed; no actual data bytes qualified. | Corrected accessible author data/generator, license, native labels, clock and execution identities remain unverified. |

**SCVIC public access.** The bounded September 23 author-source check found a 404 for the previously identified author GitHub repository. [DataCite](https://api.datacite.org/dois/10.21227/g2z5-ep97) returned metadata with no content URL or related artifact identifier. The [coauthor homepage](https://www.site.uottawa.ca/~bkantarc/) points to [DataPort](https://ieee-dataport.org/documents/scvic-apt-2021); cached primary DataPort HTML lists a 122.63 MB training set and 22.06 MB test set requiring sign-in. No accessible author artifact resolved the clock or row-to-round mapping. These checks were not repeated during this recount. Local hash agreement proves stable analyzed bytes, not author authentication of the local file.

**DAPT semantics.** The [author CSV documentation](https://gitlab.com/asu22/dapt2020/-/raw/main/csv/README.md) and [collection description](https://gitlab.com/asu22/dapt2020/-/raw/main/README.md) support the schema and five-day collection design. A capture date or public/private sensor is a collection group, not a verified independent campaign. `Activity` is an annotation and must not be used as an ordinary stage predictor.

**DSRL dependency.** The [primary publisher paper, Section 5](https://www.isecure-journal.com/article_214212_40f652111c696f5eb8da62fe518390fa.pdf) states that attack rows are CTGAN-generated from DAPT2020, while 10,000 benign rows are directly sampled from DAPT2020. The precise description is **a synthetic-attack derivative with reused benign data**. The [pinned author release](https://github.com/shadab75/DSRL-APT-2023/tree/31bd0987bf84a4616fc9f9a60410a704a0ce4967) and its MIT license were verified. Fresh public requests retrieved the paper, pinned README and license successfully; receipt hashes are recorded. Removing exact duplicates would not remove generator-training dependence. Generated attack dates must not be treated as physical execution times.

**S-DAPT release status.** The [current author arXiv record](https://arxiv.org/abs/2601.06690) returned HTTP 200 on September 23 and still marked version 2 withdrawn on April 1, 2026 for analysis errors affecting its conclusions. The [later SSRN posting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942) did not establish corrected accessible data in the preceding bounded check. This is a bounded access finding, not proof that no release exists elsewhere. Manuscript-reported counts are not substituted for measured rows.

## Implications for the paper

1. Report these as completed source-qualification and support measurements. They explain which claims the available bytes can support; they are not four failed detector experiments.
2. Preserve each native stage vocabulary. In particular, SCVIC InitialCompromise and Pivoting cannot silently become DAPT Establish Foothold.
3. Keep random development, duplicate grouping, recorded-time sensitivity, and independent-campaign validation separate. None of the reviewed sources supplies verified independent repeated-campaign identities in the acquired artifacts.
4. Do not treat DAPT and its DSRL derivative as two independent real-data confirmations. Do not claim a statistically adequate test from the minimal two/one count condition.
5. The prior PX-082 contract includes past-only completed-flow history, common evaluation anchors, capture identities, and a four-class mapping. These new sources do not supply that contract unchanged. Parsing timestamps and copying the adapter cannot create it.
6. The public evidence available in this bounded check does not resolve the missing SCVIC clock/holdout/execution information or S-DAPT corrected release. The completed support audit can be published with those limits; unqualified model arms should remain unrun.

## Primary reference for DSRL provenance

Shadabfar, H., Dehghan, M., & Sadeghian, B. (2025). DSRL-APT-2023: A new synthetic dataset for advanced persistent threats. *The ISC International Journal of Information Security, 17*(2), 107-116. https://doi.org/10.22042/isecure.2025.214212
