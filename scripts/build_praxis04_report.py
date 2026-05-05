from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


REPORT_DIR = Path("reports/praxis04_full_run")
EDA_DIR = REPORT_DIR / "eda"


PAPER_BASELINES = [
    {
        "source": "Wu et al. 2025 TSE-APT Table 4",
        "model": "RF",
        "accuracy": 96.23,
        "precision": 98.42,
        "recall": 94.11,
        "f1": 96.20,
        "fpr": 1.17,
    },
    {
        "source": "Wu et al. 2025 TSE-APT Table 4",
        "model": "MLP",
        "accuracy": 96.33,
        "precision": 98.20,
        "recall": 93.45,
        "f1": 96.19,
        "fpr": 0.58,
    },
    {
        "source": "Wu et al. 2025 TSE-APT Table 4",
        "model": "BiLSTM",
        "accuracy": 96.78,
        "precision": 98.93,
        "recall": 94.06,
        "f1": 96.25,
        "fpr": 0.77,
    },
    {
        "source": "Wu et al. 2025 TSE-APT Table 6",
        "model": "TSE-APT self-attention ensemble",
        "accuracy": 97.32,
        "precision": 99.26,
        "recall": 96.23,
        "f1": 97.51,
        "fpr": 0.69,
    },
]


def load_tuning_space() -> dict[str, str]:
    path = Path("scripts/run_praxis04_optuna.py")
    spec = importlib.util.spec_from_file_location("run_praxis04_optuna", path)
    if spec is None or spec.loader is None:
        return {}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(getattr(module, "TUNING_SPACE", {}))


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tables_dir = REPORT_DIR / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    paper_df = pd.DataFrame(PAPER_BASELINES)
    paper_df.to_csv(tables_dir / "paper_baselines_wu_2025.csv", index=False)

    cloud_df = load_cloud_pilot()
    if not cloud_df.empty:
        cloud_df.to_csv(tables_dir / "github_actions_cloud_pilot.csv", index=False)

    modeldev_df = load_modeldev_smoke()
    if not modeldev_df.empty:
        modeldev_df.to_csv(tables_dir / "modeldev_support_smoke.csv", index=False)

    write_results_chart(paper_df, cloud_df, modeldev_df, REPORT_DIR / "final_results_chart.png")
    write_report(paper_df, cloud_df, modeldev_df, REPORT_DIR / "PRAXIS04_FULL_RUN_REPORT.md")
    print(f"Wrote {REPORT_DIR / 'PRAXIS04_FULL_RUN_REPORT.md'}")


def load_cloud_pilot() -> pd.DataFrame:
    path = Path("runs/github-actions/25315742201/praxis04-cloud-pilot/runs/praxis04_headline_table.csv")
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    grouped = (
        df.groupby(["config_name", "model"], as_index=False)
        .agg(macro_f1_mean=("macro_f1", "mean"), macro_f1_std=("macro_f1", "std"), seeds=("seed", "count"))
        .sort_values("config_name")
    )
    grouped["run_family"] = "GitHub Actions cloud pilot, 10k head sample/file, pre-router-fix"
    return grouped


def load_modeldev_smoke() -> pd.DataFrame:
    rows = []
    root = Path("runs/_scratch/praxis04-modeldev-support-smoke-v6")
    if not root.exists():
        return pd.DataFrame()
    for metrics_path in sorted(root.rglob("metrics.json")):
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics = payload["metrics"]
        row = {
            "config_name": payload["config_name"],
            "model": payload["model"],
            "seed": payload["seed"],
            "macro_f1": metrics.get("macro_f1"),
            "router_entropy_mean": metrics.get("router_entropy_mean"),
            "run_family": "Local model-dev sanity, 5k head sample/file, support-floor + Macro-F1 router prior",
            "path": str(metrics_path),
        }
        for expert, expert_metrics in payload.get("expert_metrics", {}).items():
            if isinstance(expert_metrics, dict) and "macro_f1" in expert_metrics:
                row[f"expert_{expert}_macro_f1"] = expert_metrics["macro_f1"]
        rows.append(row)
    return pd.DataFrame(rows)


def write_results_chart(paper_df: pd.DataFrame, cloud_df: pd.DataFrame, modeldev_df: pd.DataFrame, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    axes[0].bar(paper_df["model"], paper_df["f1"])
    axes[0].set_title("Published TSE-APT Baselines")
    axes[0].set_ylabel("F1 (%)")
    axes[0].tick_params(axis="x", rotation=35)
    axes[0].set_ylim(90, 100)

    if not cloud_df.empty:
        axes[1].bar(cloud_df["model"], cloud_df["macro_f1_mean"] * 100)
        axes[1].set_title("Recreated Cloud Pilot")
        axes[1].set_ylabel("Macro-F1 (%)")
        axes[1].tick_params(axis="x", rotation=35)
    else:
        axes[1].text(0.5, 0.5, "No cloud pilot table found", ha="center", va="center")
        axes[1].set_axis_off()

    if not modeldev_df.empty:
        plot_df = modeldev_df.sort_values("macro_f1")
        axes[2].bar(plot_df["model"], plot_df["macro_f1"] * 100)
        axes[2].set_title("Current Model-Dev Sanity")
        axes[2].set_ylabel("Macro-F1 (%)")
        axes[2].tick_params(axis="x", rotation=35)
    else:
        axes[2].text(0.5, 0.5, "No model-dev metrics found", ha="center", va="center")
        axes[2].set_axis_off()

    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def markdown_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._"
    output = ["|" + "|".join(columns) + "|", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        output.append("|" + "|".join(format_cell(row.get(col, "")) for col in columns) + "|")
    return "\n".join(output)


def format_cell(value) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_report(paper_df: pd.DataFrame, cloud_df: pd.DataFrame, modeldev_df: pd.DataFrame, path: Path) -> None:
    eda_summary = {}
    summary_path = EDA_DIR / "eda_summary.json"
    if summary_path.exists():
        eda_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    tuning_rows = [{"parameter": key, "range": value} for key, value in load_tuning_space().items()]

    cloud_rows = cloud_df.to_dict(orient="records") if not cloud_df.empty else []
    modeldev_rows = modeldev_df.to_dict(orient="records") if not modeldev_df.empty else []

    text = f"""# Praxis 04 Full Run Report

Version: generated from local repo artifacts.

## 1. Dataset Evaluation / EDA

Dataset: CSE-CIC-IDS2018 processed flow CSVs. The raw data source is the Canadian Institute for Cybersecurity / CSE CIC-IDS2018 dataset hosted as AWS Open Data. The current local EDA found:

- Files: {eda_summary.get("n_files", "not generated")}
- Rows: {eda_summary.get("total_rows", "not generated")}
- Attack labels: {eda_summary.get("n_attack_labels", "not generated")}
- Frozen kill-chain stages: {eda_summary.get("n_stages", "not generated")}

Figures:

- ![Class distribution](eda/class_distribution.png)
- ![Stage distribution](eda/stage_distribution.png)
- ![Rows by day](eda/rows_by_day.png)
- ![Label by day heatmap](eda/label_by_day_heatmap.png)
- ![Feature distributions](eda/feature_log_distributions.png)

Code explanation:

- `scripts/eda_praxis04.py` reads every CSV in chunks, discovers the label column, counts labels by day, applies the frozen stage mapping, and writes both CSV tables and PNG figures.
- `src/praxis/praxis04/stage_mapper.py` is the audit point for the deterministic ATT&CK / kill-chain mapping.
- `src/praxis/praxis04/data_loader.py` performs numeric coercion, known-bad-row filtering, temporal splitting, optional uniform sampling, and optional support-floor movement for model-development runs.

Key dataset finding:

The CIC-IDS2018 files are strongly day- and label-confounded. A strict holdout of `Friday-02-03-2018` puts `Bot` in test while the early pilot had no `Bot` support in train or router validation. That makes the strict pilot useful as a hard generalization stress test, but not sufficient for tuning a multi-class router. For model development we added explicit support-floor settings, and they are written into the run summary so the decision is auditable.

## 2. Feature and Resampling Decisions

Feature handling:

- We use numeric CICFlowMeter columns only.
- Non-numeric identifiers such as IPs, flow IDs, timestamps, and source filenames are excluded to reduce leakage risk.
- Infinite values, NaNs, and known bad negative initial window byte rows are dropped.
- Features are standardized after the train/validation/test split.

Resampling decision:

- The current reproducible path does **not** use SMOTE by default. For this network-flow setting, SMOTE can create synthetic flow vectors that are hard to defend semantically.
- Instead, the model-dev config uses tiny real-row support floors: `min_train_rows_per_label` and `min_val_rows_per_label`.
- Class imbalance is also handled in RF by class weights and in the router by balanced class weighting / Macro-F1 initialization.
- SMOTE can be added as a later ablation, but it should be reported as synthetic oversampling, not silently folded into the main result.

## 3. Published TSE-APT Baseline

Wu et al. report the following combined CIC-IDS2018 results for their TSE-APT pipeline:

{markdown_table(paper_df.to_dict(orient="records"), ["model", "accuracy", "precision", "recall", "f1", "fpr", "source"])}

Important comparability note:

These are paper-reported percentage metrics. Our current pipeline reports Macro-F1 over the frozen label set and temporally held-out splits, so the numbers below are not direct claims of superiority over the paper until the full preregistered run is completed.

## 4. Recreated Runs and Current Experiment Numbers

Final results chart:

![Final results chart](final_results_chart.png)

### Recreated GitHub Actions Cloud Pilot

This was the first automated cloud pilot before the model-dev router/sampling fixes:

{markdown_table(cloud_rows, ["config_name", "model", "macro_f1_mean", "macro_f1_std", "seeds", "run_family"])}

Key finding:

Treatment-stage, no-stage, and oracle-stage collapsed together in this pilot. That was a useful negative debugging signal: the router was not getting meaningful stage leverage and the head-sampled pilot did not exercise enough rare-stage structure.

### Current Model-Dev Sanity Run

This local sanity run uses a 5k head sample per file, support floors, and Macro-F1 calibrated router priors:

{markdown_table(modeldev_rows, ["config_name", "model", "seed", "macro_f1", "router_entropy_mean", "expert_RF_macro_f1", "expert_MLP_macro_f1", "expert_BiLSTM_macro_f1", "expert_oracle_per_sample_expert_macro_f1"])}

Key finding:

The per-sample expert oracle is only slightly above RF in the current sanity run. That means the biggest bottleneck is expert diversity, not just routing. The stage router can only improve when at least one non-RF expert is better for a subset of stages/classes.

## 5. Optuna Tuning Plan

Run:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\run_praxis04_optuna.py --base-config configs\\praxis04-representative-pilot.json --n-trials 24 --seed 13 --output-root runs\\praxis04-optuna
```

Search space:

{markdown_table(tuning_rows, ["parameter", "range"])}

Code explanation:

- `scripts/run_praxis04_optuna.py` performs single-seed Optuna tuning on the representative pilot.
- The objective is Macro-F1.
- Each trial writes full Praxis metrics into `runs/praxis04-optuna/trial_*/metrics.json`.
- `tuning_space.json`, `trials.csv`, and `best_trial.json` are emitted for reproducibility.

## 6. Full Repeatable Run

Representative pilot:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\run_praxis04_local_pilot.py --base-config configs\\praxis04-representative-pilot.json --output-root runs\\praxis04-representative-pilot
.\\.venv\\Scripts\\python.exe scripts\\analyze_praxis04.py --results-dir runs\\praxis04-representative-pilot --output runs\\praxis04-representative-pilot\\praxis04_headline_table.csv
```

Strict preregistered full run:

```powershell
.\\scripts\\run_praxis04_all.ps1 -Python .\\.venv\\Scripts\\python.exe -Full
```

SageMaker repeatable path:

```bash
python3 scripts/submit_praxis04_sagemaker.py \\
  --region "$AWS_REGION" \\
  --instance-type ml.g5.2xlarge \\
  --volume-size 250 \\
  --wait
```

## 7. Experiment Steps

1. Download CSE-CIC-IDS2018 processed CSVs and write SHA-256 manifest.
2. Run EDA and verify class/day/stage imbalance.
3. Freeze ATT&CK / kill-chain mapping before training.
4. Train RF, MLP, and BiLSTM experts.
5. Generate expert probability outputs for train/validation/test.
6. Train or initialize global TSE-style router on validation expert outputs.
7. Train or initialize stage-conditioned router with predicted or oracle stage signals.
8. Run ablations: no-stage random signal and oracle-stage upper bound.
9. Aggregate Macro-F1, per-class F1, AUPRC, FPR@95 benign recall, router entropy, and expert diagnostics.
10. Use paired bootstrap across seeds for treatment-vs-baseline comparisons.

## 8. Current Interpretation

- The original pilot was under-informative because the router and sampling setup hid the stage effect.
- The revised model-dev path makes the stage signal auditable and keeps strict-vs-support-floor behavior explicit.
- The most important scientific question now is expert complementarity. If RF dominates every class/stage, no router can produce a meaningful gain.
- The next run should be the representative pilot plus Optuna tuning, followed by the full 5-seed run only if the pilot shows non-trivial expert diversity.

## 9. References

- Wu et al., TSE-APT, MDPI Electronics 14(15), 2025: https://www.mdpi.com/2079-9292/14/15/2924
- CSE-CIC-IDS2018 AWS Open Data: https://registry.opendata.aws/cse-cic-ids2018/
- CIC IDS 2018 dataset page: https://www.unb.ca/cic/datasets/ids-2018.html
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
