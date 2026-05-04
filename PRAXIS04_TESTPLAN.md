# Praxis 04 Test Plan

Per-Stage Weighted Ensemble Routing for APT Detection.

Extension target: TSE-APT, Wu et al., MDPI Electronics 14(15), 2025.

Version: 1.0  
Status: preregistration draft. Freeze this file before any model training.

## 1. Hypotheses

### H1

Conditioning the TSE-APT self-attention router on the predicted kill-chain stage of each sample, in addition to the input features, improves multi-class APT detection over the original TSE-APT baseline. The largest gains should appear on rare attack stages.

### H2

Per-stage routing reduces sub-model trust variance. For any given stage, the router should concentrate weight on a small subset of RF, MLP, and BiLSTM rather than distributing weight uniformly.

## 2. Falsification Criteria

The hypothesis is falsified if any of these hold after preregistered evaluation:

- Macro-F1 of the per-stage router is not statistically higher than baseline TSE-APT at `p < 0.05`, using paired bootstrap over five random seeds.
- Per-stage F1 on the rarest two attack classes does not improve by at least `+2.0` absolute F1 points vs baseline.
- Router gate entropy is not lower than the baseline router entropy.

Do not move these thresholds after seeing results.

## 3. Data

Primary dataset: CSE-CIC-IDS2018 processed traffic CSVs from the Canadian Institute for Cybersecurity / Communications Security Establishment AWS Open Data Registry.

Expected acquisition command:

```powershell
aws s3 cp --no-sign-request --region ca-central-1 "s3://cse-cic-ids2018/Processed Traffic Data for ML Algorithms/" .\data\cic-ids-2018\ --recursive
```

After download, compute SHA-256 for every CSV and record the results in `data/cic-ids-2018/manifest.json`.

Required citation:

Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization. ICISSP 2018.

## 4. Frozen Stage Mapping

The deterministic label-to-stage mapping is implemented in `src/praxis/praxis04/stage_mapping.json`.

The current mapping is:

- `FTP-BruteForce`, `SSH-BruteForce` -> Initial Access
- `Brute Force -Web`, `Brute Force -XSS`, `SQL Injection` -> Initial Access
- `Infiltration` -> Lateral Movement
- `Bot` -> Command and Control
- `DoS-*`, `DDoS-*` -> Actions on Objectives
- `Benign` -> Benign

## 5. Models

- `Baseline-Single`: RF only.
- `Baseline-TSE`: RF + MLP + BiLSTM + global self-attention router.
- `Treatment-Stage`: same sub-models, but router input is `[features, stage_logits]`.
- `Ablation-NoStage`: treatment architecture with random stage-like noise.
- `Ablation-OracleStage`: treatment architecture with ground-truth stage labels at inference time.

## 6. Seeds And Statistics

Fixed seeds:

```text
13, 42, 137, 271, 1729
```

Metrics:

- Macro-F1.
- Per-class F1, especially Infiltration and Web Attacks.
- AUPRC per class.
- False positive rate at 95% recall on Benign.
- Router gate entropy per stage.
- Inference latency p50 and p99.

Statistical test:

- Paired bootstrap on the test set with 10,000 resamples.
- Report p-values for headline comparisons.
- If seed standard deviation exceeds the claimed effect size, treat the experiment as underpowered.

## 7. Reproducibility Controls

- Seed Python, NumPy, and PyTorch from config.
- Commit every config and the frozen stage mapping.
- Save config, git SHA, training log, metrics JSON, hardware info, and data hashes for every run.
- Do not random-shuffle temporally adjacent flows into train and test.
- Hold out the Infiltration day for rare-stage evaluation when those files are present.

## 8. Outcome Policy

- If all falsification criteria pass, write up per-stage routing as the headline result.
- If Macro-F1 improves but rare-stage gains are weak, reframe around variance reduction.
- If oracle stage works but predicted stage does not, pivot to stage prediction as the bottleneck.
- If no improvement appears even with oracle stage, report a negative result.
- If improvement appears on only one seed, treat it as noise.

