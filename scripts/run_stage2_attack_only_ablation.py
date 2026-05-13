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
import torch.nn as nn
import torch.nn.functional as F
from imblearn.over_sampling import ADASYN
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


plt.style.use("dark_background")

STAGE2_NAMES = v02.STAGE_NAMES[1:]

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
            "Run a 3-seed attack-only Stage 2 MLP ablation on the trusted support-floor "
            "Unraveled split to isolate the cascade's second-stage bottleneck."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor base config JSON.")
    parser.add_argument("--run-name", required=True, help="Output folder name under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated training seeds.")
    parser.add_argument(
        "--reference-stage2-csv",
        default="runs/two-stage-support-floor-mlp-20260424/stage2_attack_only_raw.csv",
        help="Optional existing Stage 2 attack-only CSV for comparison.",
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


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(STAGE2_NAMES))),
        zero_division=0,
    )
    return {STAGE2_NAMES[index]: float(f1[index]) for index in range(len(STAGE2_NAMES))}


class ClassBalancedFocalLoss(nn.Module):
    def __init__(self, alpha: torch.Tensor | None, gamma: float = 2.0):
        super().__init__()
        self.gamma = float(gamma)
        if alpha is None:
            self.register_buffer("alpha", torch.empty(0))
        else:
            self.register_buffer("alpha", alpha.to(torch.float32))

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=1)
        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = log_pt.exp()
        focal_weight = torch.pow(1.0 - pt, self.gamma)
        if self.alpha.numel():
            focal_weight = focal_weight * self.alpha[targets]
        return (-focal_weight * log_pt).mean()


def metric_row(variant: str, seed: int, metrics: dict[str, Any], per_class: dict[str, float]) -> dict[str, Any]:
    return {
        "variant": variant,
        "seed": int(seed),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "recon_f1": float(per_class["Reconnaissance"]),
        "foothold_f1": float(per_class["Establish Foothold"]),
        "lm_f1": float(per_class["Lateral Movement"]),
        "de_f1": float(per_class["Data Exfiltration"]),
    }


def targeted_adasyn_attack_only(
    x_train: np.ndarray,
    y_train: np.ndarray,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    counts = np.bincount(y_train.astype(np.int64), minlength=len(STAGE2_NAMES))
    majority_target = int(max(counts[1], counts[2]))
    strategy: dict[int, int] = {}
    for label in (0, 3):
        if int(counts[label]) >= majority_target:
            continue
        strategy[int(label)] = majority_target

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
        "strategy": {STAGE2_NAMES[key]: int(value) for key, value in strategy.items()},
        "k_neighbors": int(min(5, k_neighbors)),
        "before_counts": {STAGE2_NAMES[index]: int(counts[index]) for index in range(len(STAGE2_NAMES))},
        "after_counts": {
            STAGE2_NAMES[index]: int(value)
            for index, value in enumerate(np.bincount(y_resampled, minlength=len(STAGE2_NAMES)))
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


def evaluate_multiclass(
    y_true: np.ndarray,
    probs: np.ndarray,
    class_names: list[str],
) -> tuple[dict[str, Any], dict[str, float]]:
    y_pred = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y_true, y_pred, probs, class_names)
    per_class = compute_per_class_f1(y_true, y_pred)
    return metrics, per_class


def build_attack_only_loss(settings: dict[str, Any], labels: np.ndarray, device: torch.device) -> nn.Module:
    loss_name = str(settings.get("loss_name", "cb_focal")).lower()
    if loss_name == "cb_focal":
        alpha = v03.compute_effective_class_weights(
            labels=labels,
            num_classes=len(STAGE2_NAMES),
            beta=float(settings.get("cb_beta", 0.999)),
        ).to(device)
        return ClassBalancedFocalLoss(
            alpha=alpha,
            gamma=float(settings.get("focal_gamma", 2.0)),
        )

    weights = v02.compute_class_weights(labels, num_classes=len(STAGE2_NAMES)).to(device)
    return nn.CrossEntropyLoss(weight=weights)


def instantiate_stage2_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(STAGE2_NAMES),
    )


def flatten_summary_columns(frame: pd.DataFrame) -> pd.DataFrame:
    flat = frame.copy()
    flat.columns = [
        f"{column}_{agg}" if agg else str(column)
        for column, agg in flat.columns.to_flat_index()
    ]
    return flat.reset_index()


def plot_variant_summary(summary_table: pd.DataFrame, output_path: Path) -> None:
    variants = summary_table["variant"].tolist()
    metrics = [
        ("macro_f1_mean", "Macro F1", "#4ecdc4"),
        ("recon_f1_mean", "Recon F1", "#ffe66d"),
        ("de_f1_mean", "DE F1", "#ff6b6b"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)
    for axis, (metric_col, title, color) in zip(axes, metrics):
        errs = summary_table[metric_col.replace("_mean", "_std")].fillna(0.0)
        axis.bar(variants, summary_table[metric_col], yerr=errs, color=color, capsize=4)
        axis.set_title(title)
        axis.grid(True, axis="y", alpha=0.2)
        axis.tick_params(axis="x", rotation=20)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


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
        variant_train_x, variant_train_y, adasyn_summary = targeted_adasyn_attack_only(
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
    model = instantiate_stage2_mlp(feature_count=int(train_x.shape[1]), params=mlp_params)
    model = model.to(device)
    criterion = build_attack_only_loss(settings=settings, labels=variant_train_y, device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(mlp_params["lr"]),
        weight_decay=float(mlp_params["weight_decay"]),
    )

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []
    for epoch in range(1, int(settings["train_epochs"]) + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0

        for xs, ys in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits, ys)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += float(loss.item()) * int(ys.numel())
            total_examples += int(ys.numel())

        _, val_probs = predict_row_model(
            model=model,
            x=val_x,
            y=val_y,
            batch_size=int(settings["tabular_batch_size"]),
            device=device,
        )
        val_metrics, _ = evaluate_multiclass(val_y, val_probs, STAGE2_NAMES)
        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": val_metrics["f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        print(
            f"    Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | val_acc={val_metrics['accuracy']:.4f}"
        )

        if float(val_metrics["f1"]) > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Stage 2 attack-only training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    val_metrics = best_metrics

    y_test_out, probs_test = predict_row_model(
        model=model,
        x=test_x,
        y=test_y,
        batch_size=int(settings["tabular_batch_size"]),
        device=device,
    )
    test_metrics, per_class = evaluate_multiclass(y_test_out, probs_test, STAGE2_NAMES)

    artifact_dir = run_dir / "seed_runs" / variant_name / f"seed_{seed}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), artifact_dir / "stage2_state_dict.pt")
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


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    base_settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, base_settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    mlp_params = v03.resolve_fixed_model_params(base_settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must define fixed_model_params for MLP.")

    seeds = parse_seeds(args.seeds)
    device = torch.device("cpu")

    v02.set_random_seed(int(base_settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=run_dir,
    )

    train_x_full, train_y_full = v02.build_row_arrays(train_df, feature_cols)
    val_x_full, val_y_full = v02.build_row_arrays(val_df, feature_cols)
    test_x_full, test_y_full = v02.build_row_arrays(test_df, feature_cols)

    train_mask = train_y_full != 0
    val_mask = val_y_full != 0
    test_mask = test_y_full != 0

    train_x = train_x_full[train_mask]
    val_x = val_x_full[val_mask]
    test_x = test_x_full[test_mask]
    train_y = train_y_full[train_mask] - 1
    val_y = val_y_full[val_mask] - 1
    test_y = test_y_full[test_mask] - 1

    raw_rows: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    for seed in seeds:
        for variant_name in VARIANT_DEFS:
            print(f"Running Stage 2 variant `{variant_name}` with seed {seed}...")
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

    raw_results = pd.DataFrame(raw_rows).sort_values(["variant", "seed"]).reset_index(drop=True)
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
        ascending=False,
        method="dense",
    )
    per_seed_ranks["recon_rank"] = per_seed_ranks.groupby("seed")["recon_f1"].rank(
        ascending=False,
        method="dense",
    )
    per_seed_ranks["de_rank"] = per_seed_ranks.groupby("seed")["de_f1"].rank(
        ascending=False,
        method="dense",
    )
    per_seed_ranks.to_csv(run_dir / "per_seed_ranks.csv", index=False)

    wins = (
        per_seed_ranks.groupby("variant")
        .agg(
            macro_seed_wins=("macro_rank", lambda values: int(np.sum(np.asarray(values) == 1))),
            recon_seed_wins=("recon_rank", lambda values: int(np.sum(np.asarray(values) == 1))),
            de_seed_wins=("de_rank", lambda values: int(np.sum(np.asarray(values) == 1))),
        )
        .reset_index()
    )
    wins.to_csv(run_dir / "seed_wins.csv", index=False)

    baseline_mean = summary_table.set_index("variant").loc["baseline_cb_focal"]
    delta_rows: list[dict[str, Any]] = []
    for _, row in summary_table.iterrows():
        delta_rows.append(
            {
                "variant": row["variant"],
                "macro_f1_mean_delta_vs_baseline": float(row["macro_f1_mean"] - baseline_mean["macro_f1_mean"]),
                "recon_f1_mean_delta_vs_baseline": float(row["recon_f1_mean"] - baseline_mean["recon_f1_mean"]),
                "de_f1_mean_delta_vs_baseline": float(row["de_f1_mean"] - baseline_mean["de_f1_mean"]),
            }
        )
    deltas = pd.DataFrame(delta_rows).sort_values("macro_f1_mean_delta_vs_baseline", ascending=False)
    deltas.to_csv(run_dir / "delta_vs_baseline.csv", index=False)

    reference_summary: dict[str, Any] = {}
    reference_path = v02.resolve_path(repo_root, args.reference_stage2_csv)
    if reference_path.exists():
        reference_frame = pd.read_csv(reference_path)
        reference_summary = {
            "path": str(reference_path),
            "mean": {
                "accuracy": float(reference_frame["accuracy"].mean()),
                "macro_f1": float(reference_frame["macro_f1"].mean()),
                "recon_f1": float(reference_frame["recon_f1"].mean()),
                "de_f1": float(reference_frame["de_f1"].mean()),
            },
        }

    best_variant = str(summary_table.iloc[0]["variant"])
    best_row = summary_table.set_index("variant").loc[best_variant]
    decision = {
        "best_variant": best_variant,
        "best_macro_f1_mean": float(best_row["macro_f1_mean"]),
        "best_recon_f1_mean": float(best_row["recon_f1_mean"]),
        "best_de_f1_mean": float(best_row["de_f1_mean"]),
        "recon_recoverable_in_attack_only_space": bool(float(best_row["recon_f1_mean"]) >= 0.5),
        "de_stable_in_attack_only_space": bool(float(best_row["de_f1_mean"]) >= 0.75),
        "attack_only_stage2_viable": bool(
            float(best_row["macro_f1_mean"]) >= 0.8
            and float(best_row["recon_f1_mean"]) >= 0.5
            and float(best_row["de_f1_mean"]) >= 0.75
        ),
    }

    plot_variant_summary(summary_table, run_dir / "stage2_ablation_mean_std.png")

    summary_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "seeds": seeds,
        "cache_path": str(cache_path),
        "cache_metadata_path": str(cache_metadata_path),
        "preprocess_summary": preprocess_summary,
        "attack_only_split_counts": {
            "train": {STAGE2_NAMES[index]: int(value) for index, value in enumerate(np.bincount(train_y, minlength=4))},
            "val": {STAGE2_NAMES[index]: int(value) for index, value in enumerate(np.bincount(val_y, minlength=4))},
            "test": {STAGE2_NAMES[index]: int(value) for index, value in enumerate(np.bincount(test_y, minlength=4))},
        },
        "mlp_params": mlp_params,
        "summary_rows": summary_table.to_dict(orient="records"),
        "seed_wins": wins.to_dict(orient="records"),
        "deltas": deltas.to_dict(orient="records"),
        "reference_summary": reference_summary,
        "decision": decision,
    }
    write_json(run_dir / "summary.json", summary_payload)

    report_lines = [
        "# Stage 2 Attack-Only MLP Ablation",
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
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    if reference_summary:
        report_lines.extend(
            [
                "## Reference Stage 2 Comparison",
                "",
                "```json",
                json.dumps(v02.coerce_json(reference_summary), indent=2),
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
