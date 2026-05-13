from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from imblearn.over_sampling import ADASYN
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")


VARIANT_DEFS = {
    "baseline_cb_focal": {
        "loss_name": "cb_focal",
        "use_adasyn": False,
        "imbalance_sampler": "proxy_rare_class",
    },
    "weighted_ce": {
        "loss_name": "weighted_ce",
        "use_adasyn": False,
        "imbalance_sampler": "proxy_rare_class",
    },
    "adasyn_cb_focal": {
        "loss_name": "cb_focal",
        "use_adasyn": True,
        "imbalance_sampler": "none",
    },
    "adasyn_weighted_ce": {
        "loss_name": "weighted_ce",
        "use_adasyn": True,
        "imbalance_sampler": "none",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the official 3-seed support-floor MLP ablation on Unraveled and "
            "produce mean/std defensibility summaries."
        )
    )
    parser.add_argument("--config", required=True, help="Base support-floor config JSON.")
    parser.add_argument(
        "--run-name",
        required=True,
        help="Output folder name to create under the config's output_dir.",
    )
    parser.add_argument(
        "--seeds",
        default="42,43,44",
        help="Comma-separated training seeds to run.",
    )
    parser.add_argument(
        "--variants",
        default="",
        help=(
            "Optional comma-separated subset of variants to run. Defaults to all "
            "registered support-floor variants."
        ),
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/unraveled-support-floor-tier12-suite-20260423/tier12_results.csv",
        help="Existing comparison table used to benchmark the MLP variants against Mamba and tree models.",
    )
    return parser.parse_args()


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def render_markdown_table(frame: pd.DataFrame, float_places: int = 4) -> str:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_float_dtype(data[column]):
            data[column] = data[column].map(lambda value: f"{value:.{float_places}f}")
    header = "| " + " | ".join(data.columns) + " |"
    divider = "| " + " | ".join(["---"] * len(data.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in data.to_numpy()]
    return "\n".join([header, divider, *rows])


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def metric_row(variant: str, seed: int, metrics: dict[str, Any], per_class: dict[str, float]) -> dict[str, Any]:
    return {
        "variant": variant,
        "seed": int(seed),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "benign_f1": float(per_class[v02.STAGE_NAMES[0]]),
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "foothold_f1": float(per_class[v02.STAGE_NAMES[2]]),
        "lm_f1": float(per_class[v02.STAGE_NAMES[3]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
    }


def targeted_adasyn(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train, minlength=len(v02.STAGE_NAMES))
    attack_majority = int(max(counts[2], counts[3]))
    strategy = {}
    for label in (1, 4):
        if int(counts[label]) >= attack_majority:
            continue
        strategy[int(label)] = attack_majority

    if not strategy:
        return x_train, y_train, {"applied": False, "reason": "targets_already_at_goal"}

    k_neighbors = min(int(counts[label]) - 1 for label in strategy)
    if k_neighbors < 1:
        return x_train, y_train, {"applied": False, "reason": "insufficient_neighbors"}

    sampler = ADASYN(
        sampling_strategy=strategy,
        random_state=random_seed,
        n_neighbors=min(5, k_neighbors),
    )
    x_resampled, y_resampled = sampler.fit_resample(x_train, y_train)
    return x_resampled, y_resampled, {
        "applied": True,
        "strategy": {v02.STAGE_NAMES[key]: int(value) for key, value in strategy.items()},
        "k_neighbors": int(min(5, k_neighbors)),
        "before_counts": {
            v02.STAGE_NAMES[index]: int(counts[index]) for index in range(len(v02.STAGE_NAMES))
        },
        "after_counts": {
            v02.STAGE_NAMES[index]: int(value)
            for index, value in enumerate(np.bincount(y_resampled, minlength=len(v02.STAGE_NAMES)))
        },
    }


def predict_row_model(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    loader = DataLoader(
        v02.RowDataset(x, y),
        batch_size=batch_size,
        shuffle=False,
    )
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


def instantiate_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    )


def run_single_variant(
    variant_name: str,
    seed: int,
    base_settings: dict[str, Any],
    mlp_params: dict[str, Any],
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    run_dir: Path,
    device: torch.device,
) -> tuple[dict[str, Any], dict[str, Any]]:
    variant_def = VARIANT_DEFS[variant_name]
    settings = dict(base_settings)
    settings["random_seed"] = int(seed)
    settings["loss_name"] = str(variant_def["loss_name"])
    settings["imbalance_sampler"] = str(variant_def["imbalance_sampler"])

    v02.set_random_seed(int(seed))
    torch.use_deterministic_algorithms(True, warn_only=True)

    variant_train_x = train_x
    variant_train_y = train_y
    adasyn_summary = {"applied": False}
    if bool(variant_def["use_adasyn"]):
        variant_train_x, variant_train_y, adasyn_summary = targeted_adasyn(
            x_train=train_x,
            y_train=train_y,
            random_seed=int(seed),
        )

    train_sampler = v03.build_row_sampler(variant_train_y, settings=settings)
    train_loader = DataLoader(
        v02.RowDataset(variant_train_x, variant_train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=train_sampler is None,
        sampler=train_sampler,
    )
    val_loader = DataLoader(
        v02.RowDataset(val_x, val_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=False,
    )
    model = instantiate_mlp(feature_count=int(train_x.shape[1]), params=mlp_params)
    model, val_metrics, history = v03.train_row_model_v03(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        train_labels=variant_train_y,
        device=device,
        settings=settings,
        lr=float(mlp_params["lr"]),
        weight_decay=float(mlp_params["weight_decay"]),
    )

    y_test_out, probs_test = predict_row_model(
        model=model,
        x=test_x,
        y=test_y,
        batch_size=int(settings["tabular_batch_size"]),
        device=device,
    )
    preds_test = np.argmax(probs_test, axis=1)
    test_metrics = v02.compute_metrics(y_test_out, preds_test, probs_test, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y_test_out, preds_test)

    artifact_dir = run_dir / "seed_runs" / variant_name / f"seed_{seed}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), artifact_dir / "mlp_state_dict.pt")
    payload = {
        "variant": variant_name,
        "seed": int(seed),
        "settings_subset": {
            "loss_name": settings["loss_name"],
            "imbalance_sampler": settings["imbalance_sampler"],
            "train_epochs": int(settings["train_epochs"]),
            "early_stopping_patience": int(settings["early_stopping_patience"]),
        },
        "best_params": mlp_params,
        "adasyn_summary": adasyn_summary,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "per_class_test_f1": per_class,
        "history": history,
    }
    write_json(artifact_dir / "results.json", payload)
    return metric_row(variant_name, seed, test_metrics, per_class), payload


def flatten_summary_columns(frame: pd.DataFrame) -> pd.DataFrame:
    flat = frame.copy()
    flat.columns = [
        f"{column}_{agg}" if agg else str(column)
        for column, agg in flat.columns.to_flat_index()
    ]
    return flat.reset_index()


def plot_seed_results(raw_results: pd.DataFrame, output_path: Path) -> None:
    variants = raw_results["variant"].drop_duplicates().tolist()
    x = np.arange(len(variants))
    width = 0.35

    macro_mean = raw_results.groupby("variant")["macro_f1"].mean().reindex(variants)
    macro_std = raw_results.groupby("variant")["macro_f1"].std(ddof=1).fillna(0.0).reindex(variants)
    de_mean = raw_results.groupby("variant")["de_f1"].mean().reindex(variants)
    de_std = raw_results.groupby("variant")["de_f1"].std(ddof=1).fillna(0.0).reindex(variants)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    axes[0].bar(x, macro_mean, yerr=macro_std, color="#4ecdc4", capsize=4)
    axes[0].set_title("Macro F1 Mean ± Std")
    axes[0].set_xticks(x, variants, rotation=20, ha="right")
    axes[0].grid(True, axis="y", alpha=0.2)

    axes[1].bar(x, de_mean, yerr=de_std, color="#ff6b6b", capsize=4)
    axes[1].set_title("DE F1 Mean ± Std")
    axes[1].set_xticks(x, variants, rotation=20, ha="right")
    axes[1].grid(True, axis="y", alpha=0.2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def parse_variants(raw: str) -> list[str]:
    variants = [item.strip() for item in raw.split(",") if item.strip()]
    if not variants:
        return list(VARIANT_DEFS)
    unknown = sorted(set(variants) - set(VARIANT_DEFS))
    if unknown:
        raise ValueError(f"Unknown variant(s): {', '.join(unknown)}")
    return variants


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, load_settings(config_path)["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    base_settings = load_settings(config_path)
    seeds = parse_seeds(args.seeds)
    variants = parse_variants(args.variants)
    mlp_params = v03.resolve_fixed_model_params(base_settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must define fixed_model_params for MLP.")

    v02.set_random_seed(int(base_settings["random_seed"]))
    device = torch.device("cpu")
    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=run_dir,
    )

    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    raw_rows: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    for seed in seeds:
        for variant_name in variants:
            print(f"Running MLP variant `{variant_name}` with seed {seed}...")
            row, payload = run_single_variant(
                variant_name=variant_name,
                seed=seed,
                base_settings=base_settings,
                mlp_params=mlp_params,
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

    raw_results = pd.DataFrame(raw_rows)
    raw_results = raw_results.sort_values(["variant", "seed"]).reset_index(drop=True)
    raw_results.to_csv(run_dir / "raw_seed_results.csv", index=False)

    summary_stats = raw_results.groupby("variant").agg(
        {
            "accuracy": ["mean", "std", "min", "max"],
            "macro_f1": ["mean", "std", "min", "max"],
            "pr_auc": ["mean", "std", "min", "max"],
            "recon_f1": ["mean", "std", "min", "max"],
            "de_f1": ["mean", "std", "min", "max"],
        }
    )
    summary_table = flatten_summary_columns(summary_stats)
    summary_table = summary_table.sort_values("macro_f1_mean", ascending=False).reset_index(drop=True)
    summary_table.to_csv(run_dir / "summary_mean_std.csv", index=False)

    per_seed_ranks = raw_results.copy()
    per_seed_ranks["macro_rank"] = per_seed_ranks.groupby("seed")["macro_f1"].rank(
        ascending=False, method="dense"
    )
    per_seed_ranks["de_rank"] = per_seed_ranks.groupby("seed")["de_f1"].rank(
        ascending=False, method="dense"
    )
    per_seed_ranks.to_csv(run_dir / "per_seed_ranks.csv", index=False)

    wins = (
        per_seed_ranks.groupby("variant")
        .agg(
            macro_seed_wins=("macro_rank", lambda values: int(np.sum(np.asarray(values) == 1))),
            de_seed_wins=("de_rank", lambda values: int(np.sum(np.asarray(values) == 1))),
        )
        .reset_index()
    )
    wins.to_csv(run_dir / "seed_wins.csv", index=False)

    summary_by_variant = summary_table.set_index("variant")
    baseline_variant = "baseline_cb_focal" if "baseline_cb_focal" in summary_by_variant.index else str(summary_table.iloc[0]["variant"])
    baseline_mean = summary_by_variant.loc[baseline_variant]
    delta_rows = []
    for _, row in summary_table.iterrows():
        delta_rows.append(
            {
                "variant": row["variant"],
                "delta_reference_variant": baseline_variant,
                "macro_f1_mean_delta_vs_baseline": float(row["macro_f1_mean"] - baseline_mean["macro_f1_mean"]),
                "de_f1_mean_delta_vs_baseline": float(row["de_f1_mean"] - baseline_mean["de_f1_mean"]),
                "recon_f1_mean_delta_vs_baseline": float(row["recon_f1_mean"] - baseline_mean["recon_f1_mean"]),
            }
        )
    deltas = pd.DataFrame(delta_rows).sort_values("macro_f1_mean_delta_vs_baseline", ascending=False)
    deltas.to_csv(run_dir / "delta_vs_baseline.csv", index=False)

    reference_path = v02.resolve_path(repo_root, args.reference_csv)
    reference_summary: dict[str, Any] = {}
    if reference_path.exists():
        reference_frame = pd.read_csv(reference_path)
        best_non_mlp = reference_frame[reference_frame["family"] != "MLP"].sort_values(
            ["macro_f1", "de_f1"], ascending=[False, False]
        ).iloc[0]
        best_mamba = reference_frame[reference_frame["family"] == "Mamba"].sort_values(
            ["macro_f1", "de_f1"], ascending=[False, False]
        ).iloc[0]
        best_tree = reference_frame[reference_frame["family"].isin(["RandomForest", "XGBoost"])].sort_values(
            ["macro_f1", "de_f1"], ascending=[False, False]
        ).iloc[0]
        reference_summary = {
            "best_non_mlp": best_non_mlp.to_dict(),
            "best_mamba": best_mamba.to_dict(),
            "best_tree": best_tree.to_dict(),
        }
    else:
        reference_frame = None

    best_variant = str(summary_table.iloc[0]["variant"])
    best_variant_rows = raw_results[raw_results["variant"] == best_variant].copy()
    repeat_seed = int(seeds[0])
    repeat_row, repeat_payload = run_single_variant(
        variant_name=best_variant,
        seed=repeat_seed,
        base_settings=base_settings,
        mlp_params=mlp_params,
        train_x=train_x,
        train_y=train_y,
        val_x=val_x,
        val_y=val_y,
        test_x=test_x,
        test_y=test_y,
        run_dir=run_dir / "repeatability_check",
        device=device,
    )
    original_repeat_row = best_variant_rows[best_variant_rows["seed"] == repeat_seed].iloc[0].to_dict()
    repeatability = {
        "variant": best_variant,
        "seed": repeat_seed,
        "original": original_repeat_row,
        "rerun": repeat_row,
        "metric_deltas": {
            key: float(repeat_row[key] - original_repeat_row[key])
            for key in ("accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1")
        },
    }
    write_json(run_dir / "repeatability_check.json", repeatability)

    defensibility = {}
    if reference_summary:
        best_summary_row = summary_table.set_index("variant").loc[best_variant]
        best_non_mlp = reference_summary["best_non_mlp"]
        best_mamba = reference_summary["best_mamba"]
        best_tree = reference_summary["best_tree"]
        defensibility = {
            "best_variant": best_variant,
            "macro_f1_std": float(best_summary_row["macro_f1_std"]),
            "de_f1_std": float(best_summary_row["de_f1_std"]),
            "wins_all_macro_seeds": bool(
                wins.set_index("variant").loc[best_variant, "macro_seed_wins"] == len(seeds)
            ),
            "mean_macro_margin_vs_best_non_mlp": float(
                best_summary_row["macro_f1_mean"] - float(best_non_mlp["macro_f1"])
            ),
            "mean_de_margin_vs_best_non_mlp": float(
                best_summary_row["de_f1_mean"] - float(best_non_mlp["de_f1"])
            ),
            "min_macro_margin_vs_best_mamba": float(
                best_variant_rows["macro_f1"].min() - float(best_mamba["macro_f1"])
            ),
            "min_macro_margin_vs_best_tree": float(
                best_variant_rows["macro_f1"].min() - float(best_tree["macro_f1"])
            ),
            "min_de_margin_vs_best_tree": float(
                best_variant_rows["de_f1"].min() - float(best_tree["de_f1"])
            ),
            "repeatability_max_abs_delta": float(
                max(abs(value) for value in repeatability["metric_deltas"].values())
            ),
        }
        defensibility["defensible_position"] = bool(
            defensibility["wins_all_macro_seeds"]
            and defensibility["mean_macro_margin_vs_best_non_mlp"] > 0.05
            and defensibility["min_macro_margin_vs_best_tree"] > 0.05
            and defensibility["min_de_margin_vs_best_tree"] > 0.50
            and defensibility["repeatability_max_abs_delta"] < 1e-9
        )

    plot_seed_results(raw_results, run_dir / "mlp_ablation_mean_std.png")

    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "reference_csv": str(reference_path),
            "seeds": seeds,
            "cache_path": str(cache_path),
            "cache_metadata_path": str(cache_metadata_path),
            "preprocess_summary": preprocess_summary,
            "mlp_params": mlp_params,
            "summary_rows": summary_table.to_dict(orient="records"),
            "seed_wins": wins.to_dict(orient="records"),
            "deltas": deltas.to_dict(orient="records"),
            "reference_summary": reference_summary,
            "defensibility": defensibility,
            "repeatability": repeatability,
        },
    )

    report_lines = [
        "# Support-Floor MLP 3-Seed Ablation",
        "",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        "",
        "## Summary Mean/Std",
        "",
        render_markdown_table(
            summary_table[
                [
                    "variant",
                    "accuracy_mean",
                    "accuracy_std",
                    "macro_f1_mean",
                    "macro_f1_std",
                    "pr_auc_mean",
                    "pr_auc_std",
                    "recon_f1_mean",
                    "recon_f1_std",
                    "de_f1_mean",
                    "de_f1_std",
                ]
            ]
        ),
        "",
        "## Seed Wins",
        "",
        render_markdown_table(wins),
        "",
        "## Delta Vs Baseline",
        "",
        render_markdown_table(deltas),
        "",
    ]

    if defensibility:
        report_lines.extend(
            [
                "## Defensibility",
                "",
                "```json",
                json.dumps(v02.coerce_json(defensibility), indent=2),
                "```",
                "",
                "## Repeatability",
                "",
                "```json",
                json.dumps(v02.coerce_json(repeatability), indent=2),
                "```",
                "",
            ]
        )

    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Raw seed results: {run_dir / 'raw_seed_results.csv'}")
    print(f"Summary mean/std: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
