# Statistically anchored synthetic experiment dataset

[Download 880 synthetic trials](grounded_20261019_final/trials.csv) · [Source audit and quality](grounded_20261019_final/quality.json) · [Hashes](grounded_20261019_final/source_manifest.json) · [RQ1–RQ3 results](grounded_run_20261019_final/REPORT.md) · [Shuffled-label control](grounded_null_run_20261019/REPORT.md)

This is a reproducible, bounded simulation anchored to recorded command and network statistics. It is closer to observed marginal behavior than the original Gaussian smoke fixture. It is **not a validated digital twin, a real matched human/AI APT dataset, or evidence for any Praxis hypothesis**. No new live collection occurred. No raw commands, outputs, addresses, credentials, or original participant IDs are published.

[Read the combined results and interpretation](GROUNDED_RESULTS.md).

## Sources actually used

| Local source | Contribution | Important limit |
| --- | --- | --- |
| GAMBiT normalized commands.json | 800 nonoverlapping 20-command blocks; positive inter-command gaps no longer than 600 seconds | Human archive; commands are controller-side proxies. 17,106 placeholder commands excluded. Normalized archive is hashed, not independently re-extracted from the original workbook. |
| Honey for the Agent Logs_final.zip | Seeded sample of 1,200 of 16,199 JSON sessions; 905 sessions with at least eight usable commands | Different SSH environments and AI models; 295 short sessions excluded. Sessions are not assumed independent operators. [Original record](https://zenodo.org/records/20818246). |
| COCHISE current run trajectories | 38 command-bearing traces after minimum-length and exact-sequence deduplication | 10 short and 11 duplicate sequences excluded. Kali/controller logs, not Windows defender sensors. Current archive only; no historical logs included. |
| DAPT local network-flow CSVs | 1,142 complete blocks of 64 consecutive flows from the first 20,000 rows per usable file | Nine usable files; one missing-header file excluded. Prefix sample, not representative whole-corpus sampling. Blocks are not time windows or APT trials. No operator-origin labels used. |

See the repository [dataset review](../../../PRAXIS_DATASET_EVALUATION.md) for source qualification. Every input file and the exact generator have SHA-256 hashes in the manifest. Raw archives must be obtained and used under their own terms; this repository does not redistribute them.

## How the sources are combined

For **both synthetic classes**, choose GAMBiT, Honey, or COCHISE with equal probability, then resample a joint command-statistics vector and perturb it with small group and trial effects. Independently draw a joint DAPT flow-statistics vector. Thus no public dataset is relabeled as a human or AI APT cohort. Cross-modal relationships are simulated, not observed. Equal source probabilities do not guarantee equal realized counts; actual draws are reported.

Small class differences are explicitly invented scenario assumptions: synthetic AI receives +0.045 command diversity, +0.12 transition entropy, +0.025 immediate repetition, +0.35 discovery-vocabulary breadth and +0.025 tool vocabulary fraction before bounding/rounding. AI timing is multiplied by 0.85, changing to 1.1 in unseen groups. These offsets **do not estimate real AI behavior**. Group effects, trial noise, synthetic scripted and benign controls are also assumptions. The modest signal deliberately avoids making classification trivial.

## Feature meanings in this simulation

| Pipeline feature | Definition / origin |
| --- | --- |
| command_diversity | Distinct first-token executable proxies / commands; bounded 0–1 |
| transition_entropy | Shannon entropy in bits of adjacent executable-token pairs |
| retry_fraction | Immediate repeated-token fraction; a repetition proxy, not verified failed-action retries |
| enumeration_breadth | Distinct first-token matches to an explicit discovery vocabulary; integer count |
| protocol_entropy | Entropy of DAPT Protocol values per 64-flow block, plus bounded noise |
| connection_diversity | Distinct destination IP/port pairs per block, perturbed and bounded 1–64 |
| outbound_fraction | Forward/(forward+backward) packets; direction proxy only, **not verified outbound traffic** |
| events_per_minute | 60 / average sampled human command gap; simulated command rate, not target sensor rate |
| interarrival_cv | Standard deviation / mean of those sampled gaps |
| peak_concurrency | 1 + Poisson(0.6); wholly assumed, not reconstructed |
| tool_pattern_fraction | First-token matches to explicit tool vocabulary / commands; bounded 0–1 |

First-token parsing is deliberately coarse: wrappers, pipelines and nested commands are not semantic executions. Command block lengths differ across sources and affect entropy/diversity. The schema remains compatible with the existing harness, but these proxies are not validated production feature definitions. Network marginals have no designed class signal. There are no missing features in this version; sensor-loss stress remains covered only by the earlier smoke fixture.

## Design and validation

880 rows: 400 synthetic human, 400 synthetic AI, 40 scripted controls and 40 benign controls. Twenty groups per primary class, twenty trials per group. Partitions: 384 training, 160 validation, 96 seen-group test, 160 unseen-group test, 80 controls. Synthetic identities are newly generated. Validation and unseen groups are disjoint; seen test uses new draws from training groups.

The source archives are calibration pools shared by the whole simulation. Source events are **not** independent real holdouts, and generated group holdouts do not establish real-world transfer. Joint resampling retains some within-source association, while clipping, noise, pooling and class offsets alter it. Quality JSON provides source and generated quantiles, counts and exclusions; no external held-out fidelity validation has been claimed.

The companion null_labels.csv keeps features and partitions fixed and randomly assigns balanced labels at group level separately in train/seen, validation and unseen cohorts. Run all model paths on both files. Null results near chance are a diagnostic, not proof of absence of leakage; a single randomization is not a significance test. Model selection still uses validation only.

## Reproduce

Install the pipeline requirements, then run from this directory with paths to your local archives:

```powershell
python grounded_synthetic.py --human PATH/commands.json --honey PATH/Logs_final.zip --cochise PATH/current/examples/run-trajectories --flows PATH/dapt2020 --output NEW_DATA_DIRECTORY
python experiment.py run --input NEW_DATA_DIRECTORY/trials.csv --output NEW_RUN_DIRECTORY
python experiment.py run --input NEW_DATA_DIRECTORY/null_labels.csv --output NEW_NULL_DIRECTORY
python verify_run.py --input NEW_DATA_DIRECTORY/trials.csv --run NEW_RUN_DIRECTORY
python verify_run.py --input NEW_DATA_DIRECTORY/null_labels.csv --run NEW_NULL_DIRECTORY
python -m pytest -q
```

Default seed: 20261019. Output directories must be new. Keep real archives outside Git. Import real matched trials only after target-side extraction, labeling and protocol qualification; do not mix synthetic and real rows for the final evidence.
