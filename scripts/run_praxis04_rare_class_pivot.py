from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from praxis.praxis04.experiment import run_experiment


VARIANTS = [
    ("praxis04-rare28-single-rf", "Single-RF", ["RF"], ["features"]),
    ("praxis04-rare28-single-mlp", "Single-MLP", ["MLP"], ["features"]),
    ("praxis04-rare28-single-bilstm", "Single-BiLSTM", ["BiLSTM"], ["features"]),
    ("praxis04-rare28-baseline-tse", "Baseline-TSE", ["RF", "MLP", "BiLSTM"], ["features"]),
    ("praxis04-rare28-treatment-stage", "Treatment-Stage", ["RF", "MLP", "BiLSTM"], ["features", "predicted_stage_logits"]),
    ("praxis04-rare28-oracle-stage", "Ablation-OracleStage", ["RF", "MLP", "BiLSTM"], ["features", "ground_truth_stage_onehot"]),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an Infilteration-day Praxis 04 pivot sweep.")
    parser.add_argument("--base-config", default="configs/praxis04-tuned-stage-router-smoke.json")
    parser.add_argument("--output-root", default="runs/praxis04-rare-class-pivot")
    parser.add_argument("--holdout-day-pattern", default="28-02-2018")
    parser.add_argument("--seeds", nargs="+", type=int, default=[13])
    parser.add_argument("--sample-rows-per-file", type=int, default=10000)
    parser.add_argument("--val-fraction-of-train-days", type=float, default=0.0)
    parser.add_argument("--router-epochs", type=int, default=None)
    parser.add_argument("--stage-classifier-model", default=None)
    parser.add_argument("--stage-class-weight", default=None)
    parser.add_argument("--stage-max-iter", type=int, default=None)
    parser.add_argument("--stage-rf-n-estimators", type=int, default=None)
    parser.add_argument("--name-suffix", default="")
    parser.add_argument(
        "--variants",
        nargs="+",
        default=[name for name, _, _, _ in VARIANTS],
        help="Config names from VARIANTS to run.",
    )
    args = parser.parse_args()

    base = json.loads(Path(args.base_config).read_text(encoding="utf-8"))
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    payloads: list[dict[str, Any]] = []

    wanted = set(args.variants)
    for name, model, submodels, router_input in VARIANTS:
        if name not in wanted:
            continue
        for seed in args.seeds:
            run_name = f"{name}{args.name_suffix}"
            config = deepcopy(base)
            config.update(
                {
                    "name": run_name,
                    "model": model,
                    "submodels": submodels,
                    "router_input": router_input,
                    "seed": int(seed),
                    "holdout_day_pattern": args.holdout_day_pattern,
                    "val_fraction_of_train_days": args.val_fraction_of_train_days,
                    "sample_rows_per_file": args.sample_rows_per_file,
                    "min_train_rows_per_label": 0,
                    "min_val_rows_per_label": 0,
                    "support_fraction_per_label": 0.0,
                }
            )
            if args.router_epochs is not None:
                config["router_epochs"] = int(args.router_epochs)
            if args.stage_classifier_model is not None:
                config["stage_classifier_model"] = args.stage_classifier_model
            if args.stage_class_weight is not None:
                config["stage_class_weight"] = args.stage_class_weight
            if args.stage_max_iter is not None:
                config["stage_max_iter"] = int(args.stage_max_iter)
            if args.stage_rf_n_estimators is not None:
                config["stage_rf_n_estimators"] = int(args.stage_rf_n_estimators)
            run_dir = output_root / f"{run_name}_seed{seed}"
            print(f"Running {run_name} seed {seed}")
            payloads.append(run_experiment(config, run_dir))

    write_summary(output_root, payloads)


def write_summary(output_root: Path, payloads: list[dict[str, Any]]) -> None:
    summary_rows = []
    per_class_rows = []
    for payload in payloads:
        metrics = payload["metrics"]
        row = {
            "config_name": payload["config_name"],
            "model": payload["model"],
            "seed": payload["seed"],
            "macro_f1": metrics["macro_f1"],
            "router_entropy_mean": metrics["router_entropy_mean"],
            "train_rows": payload["data_summary"]["train_rows"],
            "val_rows": payload["data_summary"]["val_rows"],
            "test_rows": payload["data_summary"]["test_rows"],
            "train_days": "|".join(payload["data_summary"]["train_days"]),
            "val_days": "|".join(payload["data_summary"]["val_days"]),
            "test_days": "|".join(payload["data_summary"]["test_days"]),
        }
        for class_name in ("Benign", "Bot", "Infilteration"):
            row[f"{class_name}_f1"] = metrics.get("per_class_f1", {}).get(class_name, "")
            row[f"{class_name}_support"] = metrics.get("per_class_support", {}).get(class_name, 0)
            row[f"{class_name}_predicted"] = metrics.get("per_class_predicted", {}).get(class_name, 0)
        for expert_name, expert_metrics in payload.get("expert_metrics", {}).items():
            row[f"expert_{expert_name}_macro_f1"] = expert_metrics.get("macro_f1", "")
            row[f"expert_{expert_name}_Infilteration_f1"] = expert_metrics.get("per_class_f1", {}).get("Infilteration", "")
        summary_rows.append(row)

        for class_name, f1 in metrics.get("per_class_f1", {}).items():
            per_class_rows.append(
                {
                    "config_name": payload["config_name"],
                    "model": payload["model"],
                    "seed": payload["seed"],
                    "class_name": class_name,
                    "f1": f1,
                    "support": metrics.get("per_class_support", {}).get(class_name, 0),
                    "predicted": metrics.get("per_class_predicted", {}).get(class_name, 0),
                }
            )

    write_csv(output_root / "rare_class_summary.csv", summary_rows)
    write_csv(output_root / "rare_class_per_class.csv", per_class_rows)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
