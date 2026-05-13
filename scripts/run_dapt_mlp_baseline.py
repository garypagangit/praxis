from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from imblearn.over_sampling import ADASYN
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


DAPT_REFERENCE = {
    "macro_f1_best_graph": 0.5588,
    "macro_f1_best_graph_model": "GCN-DGI",
    "roc_auc_best_graph": 0.9418,
    "roc_auc_best_graph_model": "GCN-DGI",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a cross-dataset DAPT-2020 tabular MLP attempt using the same "
            "MLP + targeted ADASYN + weighted CE recipe family that won on "
            "the trusted Unraveled support-floor benchmark."
        )
    )
    parser.add_argument(
        "--dapt-config",
        default="configs/dapt2020-local-fast.json",
        help="DAPT-2020 base config JSON.",
    )
    parser.add_argument(
        "--mlp-config",
        default="configs/praxisv03-unraveled-support-floor-baseline-20260423.json",
        help="Unraveled config that defines the official MLP recipe and fixed params.",
    )
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output folder name to create under runs/.",
    )
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated training seeds to run.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def render_markdown_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_float_dtype(data[column]):
            data[column] = data[column].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()]
    return "\n".join([header, divider, *rows])


def load_dapt_module(repo_root: Path, settings: dict[str, Any], run_dir: Path) -> Any:
    os.environ["DAPT2020_LOCAL_DATA_DIR"] = str(v02.resolve_path(repo_root, settings["local_data_dir"]))
    os.environ["DAPT2020_LOCAL_CONSOLIDATED_CSV"] = str(
        v02.resolve_path(repo_root, settings["local_consolidated_csv"])
    )
    os.environ["DAPT2020_LOCAL_OUTPUT_DIR"] = str((run_dir / "dapt_runtime").resolve())
    script_path = repo_root / "imports" / "gml_to_detect_apt_final" / "gml_to_detect_apt_final.py"
    spec = importlib.util.spec_from_file_location("praxis_dapt_cross_dataset", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load DAPT helper module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def targeted_adasyn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
    requested_n_neighbors: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train, minlength=len(v02.STAGE_NAMES))
    attack_majority = int(max(counts[2], counts[3]))
    strategy: dict[int, int] = {}
    for label in (1, 4):
        if int(counts[label]) >= attack_majority:
            continue
        strategy[int(label)] = attack_majority

    before_counts = {
        v02.STAGE_NAMES[index]: int(counts[index]) for index in range(len(v02.STAGE_NAMES))
    }
    if not strategy:
        return x_train, y_train, {
            "applied": False,
            "reason": "targets_already_at_goal",
            "requested_n_neighbors": int(requested_n_neighbors),
            "before_counts": before_counts,
            "after_counts": before_counts,
        }

    feasible_neighbors = min(int(counts[label]) - 1 for label in strategy)
    if feasible_neighbors < 1:
        return x_train, y_train, {
            "applied": False,
            "reason": "insufficient_neighbors",
            "requested_n_neighbors": int(requested_n_neighbors),
            "before_counts": before_counts,
            "after_counts": before_counts,
        }

    effective_neighbors = int(min(requested_n_neighbors, feasible_neighbors))
    sampler = ADASYN(
        sampling_strategy=strategy,
        random_state=random_seed,
        n_neighbors=effective_neighbors,
    )
    x_resampled, y_resampled = sampler.fit_resample(x_train, y_train)
    after_counts = np.bincount(y_resampled, minlength=len(v02.STAGE_NAMES))
    return x_resampled, y_resampled, {
        "applied": True,
        "strategy": {v02.STAGE_NAMES[key]: int(value) for key, value in strategy.items()},
        "requested_n_neighbors": int(requested_n_neighbors),
        "effective_n_neighbors": int(effective_neighbors),
        "before_counts": before_counts,
        "after_counts": {
            v02.STAGE_NAMES[index]: int(after_counts[index])
            for index in range(len(v02.STAGE_NAMES))
        },
    }


def instantiate_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    )


def predict_row_model(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    loader = DataLoader(v02.RowDataset(x, y), batch_size=batch_size, shuffle=False)
    model.eval()
    probs_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    with torch.no_grad():
        for xs, ys in loader:
            xs = xs.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            probs_list.append(probs.cpu().numpy())
            labels_list.append(ys.numpy())
    return np.concatenate(labels_list), np.vstack(probs_list)


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def summarize_split(frame: pd.DataFrame, split_name: str) -> list[dict[str, Any]]:
    total = max(len(frame), 1)
    counts = frame["MultiLabel"].value_counts().reindex(range(len(v02.STAGE_NAMES)), fill_value=0)
    rows: list[dict[str, Any]] = []
    for index, stage_name in enumerate(v02.STAGE_NAMES):
        value = int(counts[index])
        rows.append(
            {
                "split": split_name,
                "stage": stage_name,
                "count": value,
                "fraction": float(value / total),
            }
        )
    return rows


def build_training_settings(unraveled_settings: dict[str, Any], seed: int) -> dict[str, Any]:
    return {
        "random_seed": int(seed),
        "loss_name": "weighted_ce",
        "imbalance_sampler": "none",
        "tabular_batch_size": int(unraveled_settings["tabular_batch_size"]),
        "train_epochs": int(unraveled_settings["train_epochs"]),
        "early_stopping_patience": int(unraveled_settings["early_stopping_patience"]),
    }


def run_seed(
    seed: int,
    mlp_params: dict[str, Any],
    training_settings: dict[str, Any],
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    run_dir: Path,
    device: torch.device,
) -> tuple[dict[str, Any], dict[str, Any]]:
    v02.set_random_seed(int(seed))
    torch.use_deterministic_algorithms(True, warn_only=True)

    resampled_x, resampled_y, adasyn_summary = targeted_adasyn(
        x_train=train_x,
        y_train=train_y,
        random_seed=int(seed),
        requested_n_neighbors=5,
    )
    train_loader = DataLoader(
        v02.RowDataset(resampled_x, resampled_y),
        batch_size=int(training_settings["tabular_batch_size"]),
        shuffle=True,
    )
    val_loader = DataLoader(
        v02.RowDataset(val_x, val_y),
        batch_size=int(training_settings["tabular_batch_size"]),
        shuffle=False,
    )
    model = instantiate_mlp(feature_count=int(train_x.shape[1]), params=mlp_params)
    model, val_metrics, history = v03.train_row_model_v03(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        train_labels=resampled_y,
        device=device,
        settings=training_settings,
        lr=float(mlp_params["lr"]),
        weight_decay=float(mlp_params["weight_decay"]),
    )
    y_test_out, probs_test = predict_row_model(
        model=model,
        x=test_x,
        y=test_y,
        batch_size=int(training_settings["tabular_batch_size"]),
        device=device,
    )
    preds_test = np.argmax(probs_test, axis=1)
    test_metrics = v02.compute_metrics(y_test_out, preds_test, probs_test, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y_test_out, preds_test)

    artifact_dir = run_dir / "seed_runs" / f"seed_{seed}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), artifact_dir / "mlp_state_dict.pt")
    payload = {
        "seed": int(seed),
        "mlp_params": mlp_params,
        "training_settings": training_settings,
        "adasyn_summary": adasyn_summary,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "per_class_test_f1": per_class,
        "history": history,
    }
    write_json(artifact_dir / "results.json", payload)
    row = {
        "seed": int(seed),
        "accuracy": float(test_metrics["accuracy"]),
        "macro_f1": float(test_metrics["f1"]),
        "roc_auc": float(test_metrics["roc_auc"]) if test_metrics["roc_auc"] is not None else np.nan,
        "pr_auc": float(test_metrics["pr_auc"]) if test_metrics["pr_auc"] is not None else np.nan,
        "benign_f1": float(per_class[v02.STAGE_NAMES[0]]),
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "foothold_f1": float(per_class[v02.STAGE_NAMES[2]]),
        "lm_f1": float(per_class[v02.STAGE_NAMES[3]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
    }
    return row, payload


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    run_dir = (repo_root / "runs" / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")

    dapt_settings = load_json((repo_root / args.dapt_config).resolve())
    unraveled_settings = load_json((repo_root / args.mlp_config).resolve())
    mlp_params = dict(unraveled_settings["fixed_model_params"]["MLP"])

    dapt_module = load_dapt_module(repo_root, dapt_settings, run_dir)
    runtime_defaults = dapt_module.resolve_runtime_profile(
        max_files=dapt_settings.get("max_files"),
        sample_rate=dapt_settings.get("sample_rate"),
    )
    df, feature_cols, _ = dapt_module.load_dapt2020_with_network_context(
        max_files=dapt_settings.get("max_files"),
        sample_rate=dapt_settings.get("sample_rate") or 1.0,
        merge_networks=bool(dapt_settings.get("merge_networks", False)),
    )
    train_df, val_df, test_df, _, feature_cols = dapt_module.stratified_temporal_split_by_network(
        df=df,
        feature_cols=feature_cols,
        val_size=0.15,
        test_size=0.15,
        n_blocks=int(runtime_defaults.get("n_blocks", 10)),
        strategy=str(dapt_settings.get("strategy", "hybrid")),
    )
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    support_rows: list[dict[str, Any]] = []
    support_rows.extend(summarize_split(train_df, "train"))
    support_rows.extend(summarize_split(val_df, "val"))
    support_rows.extend(summarize_split(test_df, "test"))
    support_frame = pd.DataFrame(support_rows)
    support_frame.to_csv(run_dir / "class_support.csv", index=False)

    write_json(
        run_dir / "metadata.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "args": vars(args),
            "dapt_settings": dapt_settings,
            "mlp_recipe_source": args.mlp_config,
            "mlp_params": mlp_params,
        },
    )

    raw_rows: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    for seed in parse_seeds(args.seeds):
        print(f"Running DAPT cross-dataset MLP seed {seed}...")
        row, payload = run_seed(
            seed=seed,
            mlp_params=mlp_params,
            training_settings=build_training_settings(unraveled_settings, seed),
            train_x=train_x,
            train_y=train_y,
            val_x=val_x,
            val_y=val_y,
            test_x=test_x,
            test_y=test_y,
            run_dir=run_dir,
            device=device,
        )
        raw_rows.append(row)
        payloads.append(payload)
    raw_results = pd.DataFrame(raw_rows).sort_values("seed").reset_index(drop=True)
    raw_results.to_csv(run_dir / "raw_seed_results.csv", index=False)

    summary_frame = pd.DataFrame(
        [
            {
                "variant": "dapt_cross_dataset_mlp_adasyn_weighted_ce",
                "accuracy_mean": float(raw_results["accuracy"].mean()),
                "accuracy_std": float(raw_results["accuracy"].std(ddof=1)),
                "macro_f1_mean": float(raw_results["macro_f1"].mean()),
                "macro_f1_std": float(raw_results["macro_f1"].std(ddof=1)),
                "roc_auc_mean": float(raw_results["roc_auc"].mean()),
                "roc_auc_std": float(raw_results["roc_auc"].std(ddof=1)),
                "pr_auc_mean": float(raw_results["pr_auc"].mean()),
                "pr_auc_std": float(raw_results["pr_auc"].std(ddof=1)),
                "recon_f1_mean": float(raw_results["recon_f1"].mean()),
                "recon_f1_std": float(raw_results["recon_f1"].std(ddof=1)),
                "de_f1_mean": float(raw_results["de_f1"].mean()),
                "de_f1_std": float(raw_results["de_f1"].std(ddof=1)),
            }
        ]
    )
    summary_frame.to_csv(run_dir / "results.csv", index=False)

    comparison_frame = pd.DataFrame(
        [
            {
                "comparison": "vs_dapt_best_graph_reference",
                "macro_f1_delta": float(summary_frame.iloc[0]["macro_f1_mean"] - DAPT_REFERENCE["macro_f1_best_graph"]),
                "roc_auc_delta": float(summary_frame.iloc[0]["roc_auc_mean"] - DAPT_REFERENCE["roc_auc_best_graph"]),
            }
        ]
    )
    comparison_frame.to_csv(run_dir / "delta_vs_dapt_graph_reference.csv", index=False)

    test_de_support = int(
        support_frame[(support_frame["split"] == "test") & (support_frame["stage"] == "Data Exfiltration")]["count"].iloc[0]
    )
    limitation_note = (
        "DAPT-2020 remains structurally weak for strict DE claims because the test split has only "
        f"{test_de_support} Data Exfiltration samples in this run. This cross-dataset attempt is still "
        "useful for generalization evidence, but DE-specific conclusions must be treated as fragile."
    )
    summary_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mlp_recipe": "MLP + targeted ADASYN + weighted CE",
        "mlp_params": mlp_params,
        "mean_metrics": summary_frame.iloc[0].to_dict(),
        "reference_delta": comparison_frame.iloc[0].to_dict(),
        "limitation_note": limitation_note,
    }
    write_json(run_dir / "summary.json", summary_payload)

    report_lines = [
        "# DAPT-2020 Cross-Dataset MLP Attempt",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Run directory: `{run_dir}`",
        f"- DAPT config: `{args.dapt_config}`",
        f"- MLP recipe source: `{args.mlp_config}`",
        "",
        "## Goal",
        "",
        "Run the same winning tabular recipe family from Unraveled on DAPT-2020 so the Praxis has a concrete cross-dataset attempt instead of relying only on hardened Unraveled evidence.",
        "",
        "## Recipe",
        "",
        "```json",
        json.dumps(v02.coerce_json(mlp_params), indent=2),
        "```",
        "",
        "Training recipe details:",
        "",
        "- loss: `weighted_ce`",
        "- oversampling: targeted `ADASYN` on `Reconnaissance` and `Data Exfiltration`",
        "- ADASYN neighbors: `5`",
        "- sampler: `none`",
        "",
        "## Class Support",
        "",
        render_markdown_table(support_frame, float_places=4),
        "",
        "## Result Summary",
        "",
        render_markdown_table(summary_frame, float_places=4),
        "",
        "## Delta Versus Existing DAPT Graph Reference",
        "",
        render_markdown_table(comparison_frame, float_places=4),
        "",
        "## Limitation Note",
        "",
        limitation_note,
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Completed DAPT cross-dataset MLP run: {run_dir}")
    print(f"Macro F1 mean: {summary_frame.iloc[0]['macro_f1_mean']:.4f}")


if __name__ == "__main__":
    main()
