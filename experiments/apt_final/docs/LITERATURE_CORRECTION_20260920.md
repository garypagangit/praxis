# Minority-stage track: literature and data-access correction

**Evidence checked through: 2026-09-20 11:25:41 UTC.**

**Decision: HOLD for an independently evaluated minority-stage representation experiment. GO for bounded source acquisition and data qualification only.** This addendum corrects the September 19 literature screen. It does not alter the frozen candidate registry, registration, prior experimental receipts, or completed binary-detection results.

## 1. Material correction: S-DAPT-2026 was withdrawn

The current primary [arXiv record for S-DAPT-2026](https://arxiv.org/abs/2601.06690) identifies **version 2, April 1, 2026 at 13:24:46 UTC, as withdrawn**. The withdrawal comment includes this exact explanation:

> We have identified significant errors in the analysis that affect the main conclusions of the paper.

The earlier audit checked the January 10 version without checking the current withdrawal status. The paper must therefore **not support a positive feasibility, validated-dataset, or performance claim** in this program.

The related [E-HiDNet paper](https://arxiv.org/abs/2601.06734), which reports evaluation on S-DAPT-2026, also has a withdrawn version 2 dated April 1, 2026 at 13:24:27 UTC. Its reported performance cannot repair this evidence gap.

No corrected author-issued, publicly working dataset/generator release was verified in this bounded check. That is an access finding, not proof that no release exists. The retained [S-DAPT version 1](https://arxiv.org/html/2601.06690v1), Table II, assigns alert types directly to stages; for example, the exfiltration stage is associated with tor_alert. This creates a concrete label-leakage question for stage classification. Even a future corrected release would require generator, label, campaign, and information-access audits before use.

## 2. SCVIC-APT-2021: original license verified; usable independent groups not verified

The primary [DataCite registration for DOI 10.21227/g2z5-ep97](https://api.datacite.org/dois/10.21227/g2z5-ep97) was successfully read through its public API. Its rights metadata lists **Creative Commons Attribution 4.0 International** and links the [CC-BY-4.0 terms](https://creativecommons.org/licenses/by/4.0/legalcode). This resolves the earlier statement that the original dataset license was unverified.

The registration points to the [original IEEE DataPort page](https://ieee-dataport.org/documents/scvic-apt-2021). That landing page was unavailable to this browsing interface. **The original dataset's downloadable bytes, exact file inventory, acquisition requirements, campaign/round identifiers, and original experiment code remain unverified.** Do not infer either unrestricted access or a paywall from that retrieval failure.

A separate, working artifact exists in the [authors' repository for the 2024 dataset-limitations comparison](https://github.com/augmentedme/APT-dataset-limitation-review/tree/e7fef7a42096a8c3c4352dd82403f5f763fb1b79/scvic-apt-2021):

- Pinned commit: e7fef7a42096a8c3c4352dd82403f5f763fb1b79.
- CleanedPreprocessedSCVIC.7z: advertised size **9,023,526 bytes**, Git blob SHA-1 dfa01d844fde9d64570b8cd5263e5aa9da7f1322.
- A request for bytes 0–31 returned HTTP 206, the matching total size, and a valid 7z signature. **Only that 32-byte prefix was inspected; the full archive was not acquired, extracted, or qualified.**
- This is a comparison-author derivative, not the original dataset creators' raw release. GitHub reports no repository license; original CC-BY data rights do not by themselves establish licensing for every derivative code or added artifact.

The pinned [preprocessing script](https://github.com/augmentedme/APT-dataset-limitation-review/blob/e7fef7a42096a8c3c4352dd82403f5f763fb1b79/scvic-apt-2021/PreprocessAndSplit.py) removes flow/IP/time identifiers and uses a stratified random row split. Its two input-loading statements reference the same first-file variable. These are audit concerns, not proof that the supplied archive was produced incorrectly. Neither this code nor the uninspected archive presently establishes campaign-independent partitions.

## 3. Cached alternatives: labels exist, independent campaigns remain unresolved

A read-only recount inspected the existing local CSV files; it did not fit models or change labels.

| Existing cache | Observed support | Group limitation |
|---|---|---|
| Unraveled v03 | 435,488 rows; 7,522 exfiltration rows; 31 capture-day identifiers; 173 source files | All 435,488 cached Signature values are empty. Days/files are collection units, not verified independent campaigns. |
| DAPT2020 combined flows | 86,691 rows; 15 exfiltration rows, all on one day; five day identifiers; ten source files | No campaign identifier in this cache; rare-stage support does not enable a credible independent exfiltration test. |

The [Unraveled author repository](https://gitlab.com/asu22/unraveled) describes one sustained APT scenario alongside amateur and skilled-attacker scenarios. Its Signature definition is an attacker category, not a documented independent campaign identifier. Splitting one sustained attack across days or sensors cannot create independent APT campaigns.

These observations are consistent with the existing [HOLD data contract](../data/DATA_CONTRACT.md): source joins, clock alignment, campaign mapping, and independent per-stage support need qualification. A stage-specific flow experiment may avoid host/flow joins, but it still needs defensible group boundaries. The completed CADETS/THEIA studies used binary node labels and do not supply the missing stage annotations.

## 4. Concrete next action and release conditions

An executable next data action is to retrieve the pinned 9 MB SCVIC derivative into a new private acquisition directory, verify its Git blob identity and SHA-256, inspect its archive inventory and CSV schema, and report class counts and any preserved group keys. Do not execute the downloaded preprocessing script automatically. This action can establish what the derivative actually contains; it cannot recreate identifiers already removed.

Before a minority-stage experiment proceeds, obtain evidence-backed original campaign/round assignments and stage definitions, resolve derivative provenance/licensing, check duplicates and stage-name leakage, and freeze a group-disjoint split with adequate per-stage support. If that evidence is unavailable, restrict the data to explicitly bounded development diagnostics or select another independently qualified source.

No public data were declared acquired on the strength of a landing page. No dataset-author messages, paid downloads, cloud runs, or operative experiment changes were performed during this audit.
