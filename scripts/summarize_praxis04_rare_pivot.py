from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import f1_score


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Praxis 04 rare-day pivot runs.")
    parser.add_argument("--run-roots", nargs="+", required=True)
    parser.add_argument("--output-dir", default="reports/praxis04_full_run")
    args = parser.parse_args()

    rows = []
    for root_text in args.run_roots:
        root = Path(root_text)
        for metrics_path in sorted(root.glob("*/metrics.json")):
            rows.append(load_row(metrics_path, root.name))

    output_dir = Path(args.output_dir)
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    write_csv(tables_dir / "rare_day_pivot_seed13.csv", rows)
    write_plot(output_dir / "rare_day_pivot_seed13.png", rows)


def load_row(metrics_path: Path, run_family: str) -> dict[str, Any]:
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    config = json.loads((metrics_path.parent / "config.json").read_text(encoding="utf-8"))
    predictions = np.load(metrics_path.parent / "predictions.npz")
    y_true = predictions["y_true"]
    y_pred = predictions["y_pred"]
    supported_labels = sorted(np.unique(y_true).tolist())
    supported_macro_f1 = float(f1_score(y_true, y_pred, labels=supported_labels, average="macro", zero_division=0))

    metrics = payload["metrics"]
    stage_summary = payload.get("stage_signal_summary", {})
    row = {
        "run_family": run_family,
        "config_name": payload["config_name"],
        "model": payload["model"],
        "seed": payload["seed"],
        "holdout_day": "|".join(payload["data_summary"]["test_days"]),
        "router_epochs": config.get("router_epochs", ""),
        "router_input": "|".join(config.get("router_input", [])),
        "stage_classifier_model": config.get("stage_classifier_model", "logistic"),
        "stage_class_weight": config.get("stage_class_weight", ""),
        "supported_macro_f1": supported_macro_f1,
        "macro_f1_reported": metrics["macro_f1"],
        "benign_f1": metrics.get("per_class_f1", {}).get("Benign", ""),
        "infilteration_f1": metrics.get("per_class_f1", {}).get("Infilteration", ""),
        "benign_support": metrics.get("per_class_support", {}).get("Benign", 0),
        "infilteration_support": metrics.get("per_class_support", {}).get("Infilteration", 0),
        "benign_predicted": metrics.get("per_class_predicted", {}).get("Benign", 0),
        "infilteration_predicted": metrics.get("per_class_predicted", {}).get("Infilteration", 0),
        "router_entropy_mean": metrics.get("router_entropy_mean", ""),
        "stage_classifier_train_accuracy": stage_summary.get("stage_classifier_train_accuracy", ""),
        "stage_classifier_test_accuracy": stage_summary.get("stage_classifier_test_accuracy", ""),
    }
    for expert_name, expert_metrics in payload.get("expert_metrics", {}).items():
        row[f"expert_{expert_name}_macro_f1"] = expert_metrics.get("macro_f1", "")
        row[f"expert_{expert_name}_infilteration_f1"] = expert_metrics.get("per_class_f1", {}).get("Infilteration", "")
    return row


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "run_family",
        "config_name",
        "model",
        "seed",
        "holdout_day",
        "router_epochs",
        "router_input",
        "stage_classifier_model",
        "stage_class_weight",
        "supported_macro_f1",
        "macro_f1_reported",
        "benign_f1",
        "infilteration_f1",
        "benign_support",
        "infilteration_support",
        "benign_predicted",
        "infilteration_predicted",
        "router_entropy_mean",
        "stage_classifier_train_accuracy",
        "stage_classifier_test_accuracy",
        "expert_RF_infilteration_f1",
        "expert_MLP_infilteration_f1",
        "expert_BiLSTM_infilteration_f1",
        "expert_oracle_per_sample_expert_infilteration_f1",
    ]
    extras = sorted({key for row in rows for key in row} - set(fieldnames))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames + extras)
        writer.writeheader()
        writer.writerows(rows)


def write_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    import matplotlib.pyplot as plt

    ordered = sorted(rows, key=lambda item: (float(item["supported_macro_f1"]), float(item["infilteration_f1"])), reverse=True)
    labels = [short_label(row) for row in ordered]
    x = np.arange(len(ordered))
    supported = [float(row["supported_macro_f1"]) for row in ordered]
    inf = [float(row["infilteration_f1"]) for row in ordered]

    fig, ax = plt.subplots(figsize=(12, 5))
    width = 0.38
    ax.bar(x - width / 2, supported, width=width, label="Supported Macro-F1", color="#2f6f9f")
    ax.bar(x + width / 2, inf, width=width, label="Infilteration F1", color="#c75c2c")
    ax.set_ylim(0, max(0.8, max(supported + inf) * 1.15))
    ax.set_ylabel("F1")
    ax.set_title("Praxis 04 rare-day pivot: 28-02-2018 holdout, seed 13")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def short_label(row: dict[str, Any]) -> str:
    name = row["model"]
    if row["model"] == "Treatment-Stage" and row["stage_classifier_model"] != "logistic":
        name += f" ({row['stage_classifier_model']})"
    if str(row["config_name"]).endswith("router80"):
        name += " r80"
    if "router80_stageLogitBalanced" in str(row["config_name"]):
        name += " bal-logit"
    if "router80_stageRF" in str(row["config_name"]):
        name += " rf-stage"
    if row["model"] == "Ablation-OracleStage" and int(row.get("router_epochs") or 0) > 0:
        name = "OracleStage r80"
    return name


if __name__ == "__main__":
    main()
