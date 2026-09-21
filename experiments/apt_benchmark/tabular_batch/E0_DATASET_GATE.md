# E0: dataset audit and bounded pilot decision

Qualified September 21, 2026 UTC. **Conditional go for a 32-examples-per-class SCVIC development pilot. No dataset presently qualifies the entire proposed E1-E7 program.** E0 fitted no models and establishes no predictive improvement. Counts and hashes are in [E0_DATASET_GATE.json](E0_DATASET_GATE.json).

## What is actually available

| Dataset | Bytes examined | Main finding | Usable scope now |
|---|---|---|---|
| SCVIC-APT-2021 | Existing author training CSV: 259,120 rows, 84 columns | Only 73 InitialCompromise rows; mixed timestamps; no qualified round IDs. Author test file unavailable locally. | Deduplicated, within-training 32-per-class development screening. |
| DAPT2020 | Ten existing raw CSVs: 86,691 rows | Only 15 exfiltration flows; stages concentrate on different days. One CSV has no header. | Secondary diagnostics after explicit scope change; not the proposed all-stage few-shot grid. |
| DSRL-APT-2023 | Newly acquired pinned author CSV: 65,000 rows, 31.3 MB | CTGAN-generated from DAPT2020; five stage labels, but no independently qualified incident sequences. | Synthetic-only method/harness screening, not independent real-data validation. |
| S-DAPT-2026 | Source records; no raw dataset acquired | January paper withdrawn for analysis errors; later SSRN posting does not resolve artifact/correction qualification. | No model fitting until corrected source, raw files and data rights are qualified. |

SCVIC is tied to the [IEEE Networking Letters dataset paper](https://doi.org/10.1109/LNET.2022.3185553). Its [DataCite record](https://api.datacite.org/dois/10.21227/g2z5-ep97) and [DataPort page](https://ieee-dataport.org/documents/scvic-apt-2021) identify CC-BY 4.0. DataPort lists training and test files, but anonymous access requires a subscription/login. The original linked GitHub repository currently returns 404. The local training file's class counts match published training counts; its full bytes could not be compared against an author checksum.

DAPT2020's [MLHat 2020 paper](https://doi.org/10.1007/978-3-030-59621-7_8) describes public/private network captures. Existing local files are retained privately; their redistribution license was not independently verified. BENIGN/Benign spelling is normalized only for qualification counts. The headerless Thursday private file is read using the matching 85-column header from other source files; this retains all 4,114 rows and does not modify source bytes.

DSRL's [2025 journal article](https://doi.org/10.22042/isecure.2025.214212) and [author release](https://github.com/shadab75/DSRL-APT-2023/tree/31bd0987bf84a4616fc9f9a60410a704a0ce4967) explicitly identify CTGAN training on DAPT2020. The repository carries an MIT license. The CSV SHA256 is `883001548b93c05152ae60a1851e0cb3b939a7f3aea0808f16e4c4c997bdf7bd`. Its timestamps are generated attributes, not proof of natural campaign chronology. DAPT-to-DSRL experiments must disclose their dependency.

The current [S-DAPT arXiv record](https://arxiv.org/abs/2601.06690) still records the April 1 withdrawal. The [April 18 SSRN posting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942) exists; full-text retrieval returned HTTP 403. A manuscript posting alone is not a downloadable, licensed, qualified data release. The claimed 8,100 scenario sequences have not been inspected.

## SCVIC preparation and exact feasibility

[prepare_scvic.py](prepare_scvic.py) freezes the source and split before model fitting. It excludes Flow ID, IPs, both ports, Timestamp, labels, and all four Idle summaries. Idle Max exceeds 1e12 for every original row; sample values resemble epoch microseconds rather than meaningful idle durations. These fields remain excluded from the shared pilot feature set without attempting to reconstruct them from model outcomes.

The remaining **73 numeric predictors** are canonicalized as float64; nonfinite values become missing without fitted imputation. SHA256 fingerprints cover the complete predictor row. One conflicting-label fingerprint group (2 rows) is excluded. Another 105,199 duplicate rows are removed, retaining **153,919** unique, nonconflicting feature rows. Model-specific imputation/scaling must be fit only on that model's selected training examples.

Unique feature groups are deterministically ranked by a salted SHA256 within each label and allocated 60% fit / 20% calibration / remainder test. This removes exact feature duplication across partitions. It does **not** remove every correlated flow, near duplicate, or shared incident.

| Label | Fit pool | Calibration | Development test |
|---|---:|---:|---:|
| DataExfiltration | 316 | 105 | 106 |
| InitialCompromise | 43 | 14 | 15 |
| LateralMovement | 432 | 144 | 144 |
| NormalTraffic | 89,787 | 29,929 | 29,929 |
| Pivoting | 1,273 | 424 | 425 |
| Reconnaissance | 499 | 166 | 168 |

**Budget 32/class is supported; 64, 128, 256, 512 and 1,024/class are not supported for all six labels in this frozen split.** Do not duplicate minority examples to claim these budgets. A larger-budget experiment requires a separately declared scope, such as unequal available-label budgets, and would answer a different question.

Private prepared artifact: `C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared/DATA.npz`. SHA256: `8e8a7474d4db03b78977a3c6a48be083d60d7648dd7548788037db721e80e565`. Public receipts: [SCVIC_PREPARATION.json](SCVIC_PREPARATION.json), [verification](SCVIC_PREPARATION_VERIFICATION.json). Verification recomputed every row fingerprint, checked counts, unique groups, forbidden columns, and archive hash. It passed; this is a software/data check, not a research success.

### Why this is not a chronological or author-holdout evaluation

All SCVIC attack timestamps resolve to October 21, 2015; 220 benign rows instead show January 17, 1970. Both second-resolution ISO and minute-resolution slash formats appear. A simple chronological 60/15/10/15 support diagnostic has zero exfiltration examples in fit and calibration. No execution-round identifier was qualified. DAPT's analogous diagnostic also lacks whole stages in fit/calibration. We therefore do not represent these CSVs as supporting the proposed closed-set, all-stage temporal experiment.

The author test CSV is not present in the searched workspace/download folders. A separate research repository offers preprocessed SCVIC, but its [pinned preparation code](https://github.com/augmentedme/APT-dataset-limitation-review/blob/e7fef7a42096a8c3c4352dd82403f5f763fb1b79/scvic-apt-2021/PreprocessAndSplit.py) reads the training path twice in `combine_csv()` and then randomly splits. That artifact was not substituted for an author holdout; this observation concerns the checked-in script, not a claim about all results in its associated paper.

## Dataset-by-experiment gate

| Experiment | SCVIC local training | DAPT2020 | DSRL | S-DAPT |
|---|---|---|---|---|
| E1 few-shot model comparison | **Go at 32/class, development only** | No all-stage grid: exfiltration n=15 total | Synthetic-only screen | Blocked |
| E2 screening pipeline | Conditional: real end-to-end timing and both error types | Requires rescope | Synthetic timing/harness only | Blocked |
| E3 label-noise handling | Injected-noise development possible | Rescope required | Injected-noise synthetic check | Blocked |
| E4 conformal sets | Empirical assessment only; tiny minority calibration | No robust all-stage calibration | Synthetic assessment only | Blocked |
| E5 unknown-stage fusion | Exploratory comparison, no unseen-stage risk guarantee | No certification claim | Synthetic-only, no guarantee | Blocked |
| E6 next-stage prediction | No qualified sequence IDs | No independent scenario sequences | Generated timestamps insufficient | Blocked |
| E7 GRANDE | Optional development arm | Rescope required | Optional synthetic arm | Blocked |

With only 14 InitialCompromise calibration examples, the usual finite-sample 95% class-conditional conformal quantile requires the full class-including fallback for that class. Small sets or useful detection are not guaranteed by conformal wrapping. Exact-duplicate grouping also does not establish the exchangeability assumptions required for population coverage statements. The protocol must preserve a separate calibration role if model selection uses validation data.

## Reproduction

Run `acquire_dsrl.py --output <private>/dsrl` to fetch/hash the pinned author files. Run `audit_datasets.py --output <private>/CSV_AUDIT.json --dsrl <private>/dsrl/DSRL-APT-2023.csv` for the source-count qualification. Run `prepare_scvic.py --output <new-private-directory>` for the frozen SCVIC pilot preparation; it refuses to replace an existing populated output directory. These scripts do not train models or publish raw datasets.
