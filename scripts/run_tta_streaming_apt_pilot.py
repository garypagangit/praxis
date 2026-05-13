from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Pilot test-time adaptation for streaming APT detection using saved "
            "support-floor MLP checkpoints and the trusted held-out source_file split."
        )
    )
    parser.add_argument(
        "--source-run-dir",
        default="runs/mlp-support-floor-3seed-ablation-20260423",
        help="Run directory containing saved MLP checkpoints.",
    )
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--run-name", default="tta-streaming-apt-pilot-20260509")
    parser.add_argument("--config", default=None, help="Optional config override; defaults to source summary config_path.")
    parser.add_argument("--seeds", default="", help="Optional comma-separated seeds; defaults to source summary seeds.")
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--tent-lrs", default="1e-5,5e-5,1e-4")
    parser.add_argument("--tent-steps", type=int, default=1)
    parser.add_argument("--confidence-thresholds", default="0.70,0.80,0.90")
    return parser.parse_args()


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def parse_float_csv(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one value is required.")
    return values


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


def instantiate_mlp(feature_count: int, params: dict[str, Any]) -> torch.nn.Module:
    return v02.MLPStageClassifier(
        num_features=feature_count,
        hidden_dim=int(params["hidden_dim"]),
        num_layers=int(params["num_layers"]),
        dropout=float(params["dropout"]),
        num_classes=len(v02.STAGE_NAMES),
    )


def compute_per_class_f1(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    _, _, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(v02.STAGE_NAMES))),
        zero_division=0,
    )
    return {v02.STAGE_NAMES[index]: float(f1[index]) for index in range(len(v02.STAGE_NAMES))}


def metric_row(
    method: str,
    seed: int,
    split: str,
    metrics: dict[str, Any],
    per_class: dict[str, float],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "method": method,
        "seed": int(seed),
        "split": split,
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["f1"]),
        "pr_auc": float(metrics["pr_auc"]) if metrics["pr_auc"] is not None else np.nan,
        "benign_f1": float(per_class[v02.STAGE_NAMES[0]]),
        "recon_f1": float(per_class[v02.STAGE_NAMES[1]]),
        "foothold_f1": float(per_class[v02.STAGE_NAMES[2]]),
        "lm_f1": float(per_class[v02.STAGE_NAMES[3]]),
        "de_f1": float(per_class[v02.STAGE_NAMES[4]]),
    }
    if extra:
        row.update(extra)
    return row


def predict_probs(model: torch.nn.Module, x: np.ndarray, batch_size: int, device: torch.device) -> np.ndarray:
    loader = DataLoader(
        TensorDataset(torch.from_numpy(x.astype(np.float32))),
        batch_size=batch_size,
        shuffle=False,
    )
    model.eval()
    probs: list[np.ndarray] = []
    with torch.no_grad():
        for (xs,) in loader:
            logits = model(xs.to(device))
            probs.append(torch.softmax(logits, dim=1).cpu().numpy())
    return np.vstack(probs)


def evaluate_probs(
    method: str,
    seed: int,
    split: str,
    y: np.ndarray,
    probs: np.ndarray,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pred = np.argmax(probs, axis=1)
    metrics = v02.compute_metrics(y, pred, probs, v02.STAGE_NAMES)
    per_class = compute_per_class_f1(y, pred)
    return metric_row(method, seed, split, metrics, per_class, extra)


def adapt_bn_stats(model: torch.nn.Module, x: np.ndarray, batch_size: int, device: torch.device) -> np.ndarray:
    loader = DataLoader(
        TensorDataset(torch.from_numpy(x.astype(np.float32))),
        batch_size=batch_size,
        shuffle=False,
    )
    set_bn_train_dropout_eval(model)
    probs: list[np.ndarray] = []
    with torch.no_grad():
        for (xs,) in loader:
            logits = model(xs.to(device))
            probs.append(torch.softmax(logits, dim=1).cpu().numpy())
    model.eval()
    return np.vstack(probs)


def entropy_loss(logits: torch.Tensor) -> torch.Tensor:
    probs = torch.softmax(logits, dim=1)
    log_probs = torch.log_softmax(logits, dim=1)
    return -(probs * log_probs).sum(dim=1).mean()


def configure_tent_model(model: torch.nn.Module) -> list[torch.nn.Parameter]:
    set_bn_train_dropout_eval(model)
    for param in model.parameters():
        param.requires_grad_(False)

    params: list[torch.nn.Parameter] = []
    for module in model.modules():
        if isinstance(module, torch.nn.BatchNorm1d):
            module.weight.requires_grad_(True)
            module.bias.requires_grad_(True)
            params.extend([module.weight, module.bias])
    if not params:
        raise RuntimeError("TENT requires BatchNorm affine parameters, but none were found.")
    return params


def set_bn_train_dropout_eval(model: torch.nn.Module) -> None:
    model.eval()
    for module in model.modules():
        if isinstance(module, torch.nn.BatchNorm1d):
            module.train()


def adapt_tent_stream(
    model: torch.nn.Module,
    x: np.ndarray,
    batch_size: int,
    device: torch.device,
    lr: float,
    steps: int,
    confidence_threshold: float | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    loader = DataLoader(
        TensorDataset(torch.from_numpy(x.astype(np.float32))),
        batch_size=batch_size,
        shuffle=False,
    )
    params = configure_tent_model(model)
    optimizer = torch.optim.Adam(params, lr=float(lr))
    probs: list[np.ndarray] = []
    update_batches = 0
    skipped_batches = 0
    selected_examples = 0

    for (xs,) in loader:
        xs = xs.to(device)
        for _ in range(max(int(steps), 1)):
            optimizer.zero_grad()
            logits = model(xs)
            if confidence_threshold is None:
                loss = entropy_loss(logits)
                selected_count = int(xs.shape[0])
            else:
                batch_probs = torch.softmax(logits.detach(), dim=1)
                mask = batch_probs.max(dim=1).values >= float(confidence_threshold)
                if not bool(mask.any()):
                    skipped_batches += 1
                    continue
                loss = entropy_loss(logits[mask])
                selected_count = int(mask.sum().item())
            loss.backward()
            optimizer.step()
            update_batches += 1
            selected_examples += selected_count

        with torch.no_grad():
            logits = model(xs)
            probs.append(torch.softmax(logits, dim=1).cpu().numpy())

    model.eval()
    return np.vstack(probs), {
        "lr": float(lr),
        "steps": int(steps),
        "confidence_threshold": confidence_threshold if confidence_threshold is None else float(confidence_threshold),
        "update_batches": int(update_batches),
        "skipped_batches": int(skipped_batches),
        "selected_examples": int(selected_examples),
    }


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby(["method", "split"])
        .agg(
            accuracy_mean=("accuracy", "mean"),
            accuracy_std=("accuracy", "std"),
            macro_f1_mean=("macro_f1", "mean"),
            macro_f1_std=("macro_f1", "std"),
            pr_auc_mean=("pr_auc", "mean"),
            pr_auc_std=("pr_auc", "std"),
            benign_f1_mean=("benign_f1", "mean"),
            recon_f1_mean=("recon_f1", "mean"),
            de_f1_mean=("de_f1", "mean"),
        )
        .reset_index()
    )


def add_test_deltas(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    frozen = out[(out["method"] == "frozen") & (out["split"] == "test")]
    if frozen.empty:
        return out
    base = frozen.iloc[0]
    for metric in ["accuracy", "macro_f1", "pr_auc", "benign_f1", "recon_f1", "de_f1"]:
        out[f"{metric}_delta_vs_frozen"] = np.where(
            out["split"] == "test",
            out[f"{metric}_mean"] - float(base[f"{metric}_mean"]),
            np.nan,
        )
    return out


def main() -> None:
    args = parse_args()
    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    source_summary = json.loads((source_run_dir / "summary.json").read_text(encoding="utf-8"))
    config_path = Path(args.config).resolve() if args.config else Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds) if str(args.seeds).strip() else [int(seed) for seed in source_summary["seeds"]]
    tent_lrs = parse_float_csv(args.tent_lrs)
    confidence_thresholds = parse_float_csv(args.confidence_thresholds)
    batch_size = int(args.batch_size)
    device = torch.device("cpu")

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")

    print(f"Loading trusted split from {config_path}...")
    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=run_dir,
    )
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)

    raw_rows: list[dict[str, Any]] = []
    adaptation_rows: list[dict[str, Any]] = []

    methods: list[dict[str, Any]] = [{"method": "frozen", "kind": "frozen"}]
    methods.append({"method": "bn_adapt", "kind": "bn"})
    for lr in tent_lrs:
        methods.append({"method": f"tent_lr{lr:g}", "kind": "tent", "lr": lr, "confidence_threshold": None})
    for lr in tent_lrs:
        for threshold in confidence_thresholds:
            methods.append(
                {
                    "method": f"tent_conf{threshold:.2f}_lr{lr:g}",
                    "kind": "tent",
                    "lr": lr,
                    "confidence_threshold": threshold,
                }
            )

    for seed in seeds:
        print(f"\nSeed {seed}: evaluating frozen and TTA variants...")
        state_path = source_run_dir / "seed_runs" / str(args.variant) / f"seed_{seed}" / "mlp_state_dict.pt"
        if not state_path.exists():
            raise FileNotFoundError(f"Missing checkpoint: {state_path}")

        base_model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params).to(device)
        base_model.load_state_dict(torch.load(state_path, map_location=device))
        base_state = copy.deepcopy(base_model.state_dict())

        for method_spec in methods:
            method_name = str(method_spec["method"])
            kind = str(method_spec["kind"])
            for split_name, x_split, y_split in (("val", val_x, val_y), ("test", test_x, test_y)):
                model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params).to(device)
                model.load_state_dict(copy.deepcopy(base_state))

                if kind == "frozen":
                    probs = predict_probs(model, x_split, batch_size, device)
                    extra = {}
                elif kind == "bn":
                    probs = adapt_bn_stats(model, x_split, batch_size, device)
                    extra = {}
                elif kind == "tent":
                    probs, extra = adapt_tent_stream(
                        model=model,
                        x=x_split,
                        batch_size=batch_size,
                        device=device,
                        lr=float(method_spec["lr"]),
                        steps=int(args.tent_steps),
                        confidence_threshold=method_spec["confidence_threshold"],
                    )
                    adaptation_rows.append({"method": method_name, "seed": int(seed), "split": split_name, **extra})
                else:
                    raise ValueError(f"Unknown method kind: {kind}")

                raw_rows.append(evaluate_probs(method_name, seed, split_name, y_split, probs, extra))

    raw_frame = pd.DataFrame(raw_rows).sort_values(["method", "split", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(run_dir / "raw_results.csv", index=False)
    if adaptation_rows:
        pd.DataFrame(adaptation_rows).to_csv(run_dir / "adaptation_details.csv", index=False)

    summary_frame = add_test_deltas(summarize(raw_frame))
    summary_frame = summary_frame.sort_values(
        ["split", "macro_f1_mean", "de_f1_mean", "recon_f1_mean"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    test_summary = summary_frame[summary_frame["split"] == "test"].copy()
    best_test = test_summary.sort_values(
        ["macro_f1_mean", "de_f1_mean", "recon_f1_mean"],
        ascending=[False, False, False],
    ).iloc[0]
    decision = {
        "best_test_method": best_test.to_dict(),
        "any_test_macro_gain": bool((test_summary["macro_f1_delta_vs_frozen"] > 0.0).any()),
        "any_test_recon_gain": bool((test_summary["recon_f1_delta_vs_frozen"] > 0.0).any()),
        "any_test_de_gain": bool((test_summary["de_f1_delta_vs_frozen"] > 0.0).any()),
    }
    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_run_dir": str(source_run_dir),
            "variant": str(args.variant),
            "config_path": str(config_path),
            "seeds": seeds,
            "batch_size": batch_size,
            "tent_lrs": tent_lrs,
            "tent_steps": int(args.tent_steps),
            "confidence_thresholds": confidence_thresholds,
            "preprocess_summary": preprocess_summary,
            "decision": decision,
        },
    )

    report_lines = [
        "# TTA Streaming APT Pilot",
        "",
        f"Source checkpoints: `{source_run_dir}`",
        f"Variant: `{args.variant}`",
        f"Config: `{config_path.name}`",
        f"Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Raw results: {run_dir / 'raw_results.csv'}")
    print(f"Summary: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
