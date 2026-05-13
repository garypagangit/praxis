from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_stage2_de_multiplier_suite import (
    FAMILY_DEFS,
    build_attack_only_loss,
    compute_attack_only_per_class_f1,
    instantiate_stage2_mlp,
    parse_float_list,
    parse_seeds,
    predict_row_model,
    render_markdown_table,
    targeted_adasyn_attack_only,
    write_json,
)
from scripts.run_two_stage_feature_subset_revision import (
    STAGE2_NAMES,
    build_end_to_end_outputs,
    build_feature_subsets,
    choose_threshold,
    compute_per_class_f1 as compute_full_per_class_f1,
    compute_recon_auc_scores,
    predict_probs,
    set_seed,
    train_stage1_mlp,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rerun a small set of Stage 2 variants while selecting the checkpoint by "
            "end-to-end validation performance instead of attack-only validation."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor base config JSON.")
    parser.add_argument("--run-name", required=True, help="Output folder under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated seeds.")
    parser.add_argument("--candidate", default="recon_top30", help="Stage 1 feature-subset candidate.")
    parser.add_argument(
        "--variants",
        default="adasyn_weighted_ce:1.0,adasyn_weighted_ce:2.0,adasyn_cb_focal:1.25",
        help="Comma-separated family:de_multiplier entries.",
    )
    parser.add_argument(
        "--reference-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage reference raw results CSV.",
    )
    parser.add_argument(
        "--reference-end2end-raw",
        default="runs/stage2-de-multiplier-suite-20260428/end_to_end_raw.csv",
        help="Previous attack-only-selection end-to-end raw CSV for comparison.",
    )
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    return parser.parse_args()


def parse_variants(raw: str) -> list[tuple[str, float]]:
    variants: list[tuple[str, float]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        family, value = item.split(":", 1)
        family = family.strip()
        if family not in FAMILY_DEFS:
            raise ValueError(f"Unknown family in variants: {family}")
        variants.append((family, float(value.strip())))
    if not variants:
        raise ValueError("At least one variant is required.")
    return variants


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def train_stage2_end2end_selected(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x_attack: np.ndarray,
    val_y_attack: np.ndarray,
    full_val_x: np.ndarray,
    val_stage1_probs: np.ndarray,
    val_original_y: np.ndarray,
    stage1_threshold: float,
    mlp_params: dict[str, Any],
    base_settings: dict[str, Any],
    loss_name: str,
    stage_loss_multipliers: list[float],
    device: torch.device,
) -> tuple[torch.nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = instantiate_stage2_mlp(feature_count=int(train_x.shape[1]), params=mlp_params).to(device)
    train_sampler = v03.build_row_sampler(train_y, settings=base_settings)
    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(base_settings["tabular_batch_size"]),
        shuffle=train_sampler is None,
        sampler=train_sampler,
    )
    criterion = build_attack_only_loss(
        loss_name=loss_name,
        labels=train_y,
        device=device,
        settings=base_settings,
        stage_loss_multipliers=stage_loss_multipliers,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(mlp_params["lr"]),
        weight_decay=float(mlp_params["weight_decay"]),
    )

    best_state: dict[str, Any] | None = None
    best_snapshot: dict[str, Any] | None = None
    best_key: tuple[float, float, float, float] | None = None
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(base_settings["train_epochs"]) + 1):
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

        _, val_attack_probs = predict_row_model(
            model=model,
            x=val_x_attack,
            y=val_y_attack,
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        val_attack_pred = np.argmax(val_attack_probs, axis=1)
        val_attack_metrics = v02.compute_metrics(val_y_attack, val_attack_pred, val_attack_probs, STAGE2_NAMES)
        val_attack_per_class = compute_attack_only_per_class_f1(val_y_attack, val_attack_pred)

        _, full_val_stage2_probs = predict_row_model(
            model=model,
            x=full_val_x,
            y=np.zeros(len(full_val_x), dtype=np.int64),
            batch_size=int(base_settings["tabular_batch_size"]),
            device=device,
        )
        end_val_pred, end_val_probs = build_end_to_end_outputs(
            stage1_probs=val_stage1_probs,
            stage2_probs=full_val_stage2_probs,
            threshold=float(stage1_threshold),
        )
        end_val_metrics = v02.compute_metrics(val_original_y, end_val_pred, end_val_probs, v02.STAGE_NAMES)
        end_val_per_class = compute_full_per_class_f1(val_original_y, end_val_pred)

        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "attack_val_macro_f1": float(val_attack_metrics["f1"]),
                "attack_val_de_f1": float(val_attack_per_class["Data Exfiltration"]),
                "end_val_macro_f1": float(end_val_metrics["f1"]),
                "end_val_recon_f1": float(end_val_per_class["Reconnaissance"]),
                "end_val_de_f1": float(end_val_per_class["Data Exfiltration"]),
            }
        )
        print(
            f"      Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"end_val_macro={end_val_metrics['f1']:.4f} | "
            f"end_val_de={end_val_per_class['Data Exfiltration']:.4f}"
        )

        current_key = (
            float(end_val_metrics["f1"]),
            float(end_val_per_class["Data Exfiltration"]),
            float(end_val_per_class["Reconnaissance"]),
            float(val_attack_metrics["f1"]),
        )
        if best_key is None or current_key > best_key:
            best_key = current_key
            best_snapshot = {
                "attack_val_metrics": val_attack_metrics,
                "attack_val_per_class": val_attack_per_class,
                "end_val_metrics": end_val_metrics,
                "end_val_per_class": end_val_per_class,
                "selected_epoch": epoch,
            }
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= int(base_settings["early_stopping_patience"]):
                break

    if best_state is None or best_snapshot is None:
        raise RuntimeError("End-to-end Stage 2 training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_snapshot, history


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    base_settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, base_settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds)
    variants = parse_variants(args.variants)
    device = torch.device("cpu")
    mlp_params = v03.resolve_fixed_model_params(base_settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must define fixed_model_params for MLP.")

    v02.set_random_seed(int(base_settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = v02.load_or_build_cache(base_settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=base_settings,
        gml=gml,
        run_dir=run_dir,
    )

    overall_importance = pd.read_csv(v02.resolve_path(repo_root, args.s6_feature_importance_csv))
    overall_importance = overall_importance[
        (overall_importance["dataset"] == "Unraveled") & (overall_importance["model"] == "MLP")
    ][["feature", "importance"]]
    recon_auc_df = compute_recon_auc_scores(train_df, feature_cols)
    candidates = build_feature_subsets(feature_cols, overall_importance, recon_auc_df)
    if str(args.candidate) not in candidates:
        raise ValueError(f"Unknown candidate: {args.candidate}")
    stage1_features = candidates[str(args.candidate)]

    train_x_stage1 = train_df[stage1_features].values.astype(np.float32)
    val_x_stage1 = val_df[stage1_features].values.astype(np.float32)
    test_x_stage1 = test_df[stage1_features].values.astype(np.float32)
    train_binary_y = (train_df["MultiLabel"].values != 0).astype(np.int64)
    val_binary_y = (val_df["MultiLabel"].values != 0).astype(np.int64)
    test_binary_y = (test_df["MultiLabel"].values != 0).astype(np.int64)
    val_original_y = val_df["MultiLabel"].values.astype(np.int64)
    test_original_y = test_df["MultiLabel"].values.astype(np.int64)

    full_val_x = val_df[feature_cols].values.astype(np.float32)
    full_test_x = test_df[feature_cols].values.astype(np.float32)

    attack_train_mask = train_df["MultiLabel"].values != 0
    attack_val_mask = val_df["MultiLabel"].values != 0
    attack_test_mask = test_df["MultiLabel"].values != 0
    train_x_stage2 = train_df.loc[attack_train_mask, feature_cols].values.astype(np.float32)
    val_x_stage2 = val_df.loc[attack_val_mask, feature_cols].values.astype(np.float32)
    test_x_stage2 = test_df.loc[attack_test_mask, feature_cols].values.astype(np.float32)
    train_y_stage2 = train_df.loc[attack_train_mask, "MultiLabel"].values.astype(np.int64) - 1
    val_y_stage2 = val_df.loc[attack_val_mask, "MultiLabel"].values.astype(np.int64) - 1
    test_y_stage2 = test_df.loc[attack_test_mask, "MultiLabel"].values.astype(np.int64) - 1

    reference_single = pd.read_csv(v02.resolve_path(repo_root, args.reference_csv))
    reference_single = reference_single[reference_single["variant"] == "adasyn_weighted_ce"].sort_values("seed")
    reference_prev = pd.read_csv(v02.resolve_path(repo_root, args.reference_end2end_raw))

    stage1_cache: dict[int, dict[str, Any]] = {}
    for seed in seeds:
        print(f"\nTraining fixed Stage 1 for seed {seed}...")
        set_seed(seed)
        stage1_model = train_stage1_mlp(
            train_x=train_x_stage1,
            train_y=train_binary_y,
            val_x=val_x_stage1,
            val_y=val_binary_y,
            params=mlp_params,
            settings=base_settings,
            device=device,
        )
        val_stage1_probs = predict_probs(
            stage1_model,
            val_x_stage1,
            val_binary_y,
            int(base_settings["tabular_batch_size"]),
            device,
        )
        test_stage1_probs = predict_probs(
            stage1_model,
            test_x_stage1,
            test_binary_y,
            int(base_settings["tabular_batch_size"]),
            device,
        )
        threshold_row = choose_threshold(val_original_y, val_binary_y, val_stage1_probs)
        stage1_cache[seed] = {
            "threshold": float(threshold_row["threshold"]),
            "val_stage1_probs": val_stage1_probs,
            "test_stage1_probs": test_stage1_probs,
        }

    raw_rows: list[dict[str, Any]] = []
    for family_name, de_multiplier in variants:
        variant_name = f"{family_name}_de{de_multiplier:.2f}".replace(".", "p")
        stage_loss_multipliers = [1.0, 1.0, 1.0, float(de_multiplier)]
        print(f"\nRunning end-to-end-selected Stage 2 `{family_name}` with DE multiplier {de_multiplier:.2f}...")
        for seed in seeds:
            set_seed(seed)
            variant_train_x = train_x_stage2
            variant_train_y = train_y_stage2
            adasyn_summary = {"applied": False}
            if FAMILY_DEFS[family_name]["use_adasyn"]:
                variant_train_x, variant_train_y, adasyn_summary = targeted_adasyn_attack_only(
                    x_train=train_x_stage2,
                    y_train=train_y_stage2,
                    random_seed=int(seed),
                )

            model, selection_snapshot, history = train_stage2_end2end_selected(
                train_x=variant_train_x,
                train_y=variant_train_y,
                val_x_attack=val_x_stage2,
                val_y_attack=val_y_stage2,
                full_val_x=full_val_x,
                val_stage1_probs=stage1_cache[seed]["val_stage1_probs"],
                val_original_y=val_original_y,
                stage1_threshold=float(stage1_cache[seed]["threshold"]),
                mlp_params=mlp_params,
                base_settings=base_settings,
                loss_name=str(FAMILY_DEFS[family_name]["loss_name"]),
                stage_loss_multipliers=stage_loss_multipliers,
                device=device,
            )

            y_attack_out, attack_probs = predict_row_model(
                model=model,
                x=test_x_stage2,
                y=test_y_stage2,
                batch_size=int(base_settings["tabular_batch_size"]),
                device=device,
            )
            attack_pred = np.argmax(attack_probs, axis=1)
            attack_metrics = v02.compute_metrics(y_attack_out, attack_pred, attack_probs, STAGE2_NAMES)
            attack_per_class = compute_attack_only_per_class_f1(y_attack_out, attack_pred)

            _, full_test_probs = predict_row_model(
                model=model,
                x=full_test_x,
                y=np.zeros(len(full_test_x), dtype=np.int64),
                batch_size=int(base_settings["tabular_batch_size"]),
                device=device,
            )
            end_test_pred, end_test_probs = build_end_to_end_outputs(
                stage1_probs=stage1_cache[seed]["test_stage1_probs"],
                stage2_probs=full_test_probs,
                threshold=float(stage1_cache[seed]["threshold"]),
            )
            end_test_metrics = v02.compute_metrics(test_original_y, end_test_pred, end_test_probs, v02.STAGE_NAMES)
            end_test_per_class = compute_full_per_class_f1(test_original_y, end_test_pred)

            prev_row = reference_prev[
                (reference_prev["family"] == family_name)
                & (reference_prev["de_multiplier"] == float(de_multiplier))
                & (reference_prev["seed"] == int(seed))
            ].iloc[0]
            single_row = reference_single[reference_single["seed"] == int(seed)].iloc[0]

            raw_rows.append(
                {
                    "variant": variant_name,
                    "family": family_name,
                    "de_multiplier": float(de_multiplier),
                    "seed": int(seed),
                    "selected_epoch": int(selection_snapshot["selected_epoch"]),
                    "threshold": float(stage1_cache[seed]["threshold"]),
                    "attack_accuracy": float(attack_metrics["accuracy"]),
                    "attack_macro_f1": float(attack_metrics["f1"]),
                    "attack_recon_f1": float(attack_per_class["Reconnaissance"]),
                    "attack_de_f1": float(attack_per_class["Data Exfiltration"]),
                    "end_accuracy": float(end_test_metrics["accuracy"]),
                    "end_macro_f1": float(end_test_metrics["f1"]),
                    "end_pr_auc": float(end_test_metrics["pr_auc"]) if end_test_metrics["pr_auc"] is not None else np.nan,
                    "end_recon_f1": float(end_test_per_class["Reconnaissance"]),
                    "end_de_f1": float(end_test_per_class["Data Exfiltration"]),
                    "delta_vs_prev_end_macro": float(end_test_metrics["f1"] - prev_row["macro_f1"]),
                    "delta_vs_prev_end_de": float(end_test_per_class["Data Exfiltration"] - prev_row["de_f1"]),
                    "delta_vs_single_end_macro": float(end_test_metrics["f1"] - single_row["macro_f1"]),
                    "delta_vs_single_end_de": float(end_test_per_class["Data Exfiltration"] - single_row["de_f1"]),
                }
            )

            artifact_dir = run_dir / "seed_runs" / variant_name / f"seed_{seed}"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), artifact_dir / "stage2_state_dict.pt")
            write_json(
                artifact_dir / "results.json",
                {
                    "variant": variant_name,
                    "family": family_name,
                    "seed": int(seed),
                    "de_multiplier": float(de_multiplier),
                    "stage_loss_multipliers": stage_loss_multipliers,
                    "adasyn_summary": adasyn_summary,
                    "selection_snapshot": selection_snapshot,
                    "history": history,
                    "attack_only_test_metrics": attack_metrics,
                    "attack_only_test_per_class_f1": attack_per_class,
                    "end_to_end_test_metrics": end_test_metrics,
                    "end_to_end_test_per_class_f1": end_test_per_class,
                },
            )

    raw_frame = pd.DataFrame(raw_rows).sort_values(["family", "de_multiplier", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(run_dir / "raw_results.csv", index=False)

    summary_frame = raw_frame.groupby(["family", "de_multiplier"]).agg(
        end_accuracy_mean=("end_accuracy", "mean"),
        end_accuracy_std=("end_accuracy", "std"),
        end_macro_f1_mean=("end_macro_f1", "mean"),
        end_macro_f1_std=("end_macro_f1", "std"),
        end_pr_auc_mean=("end_pr_auc", "mean"),
        end_pr_auc_std=("end_pr_auc", "std"),
        end_recon_f1_mean=("end_recon_f1", "mean"),
        end_recon_f1_std=("end_recon_f1", "std"),
        end_de_f1_mean=("end_de_f1", "mean"),
        end_de_f1_std=("end_de_f1", "std"),
        delta_vs_prev_end_macro_mean=("delta_vs_prev_end_macro", "mean"),
        delta_vs_prev_end_de_mean=("delta_vs_prev_end_de", "mean"),
        delta_vs_single_end_macro_mean=("delta_vs_single_end_macro", "mean"),
        delta_vs_single_end_de_mean=("delta_vs_single_end_de", "mean"),
    ).reset_index()
    summary_frame = summary_frame.sort_values(["end_macro_f1_mean", "end_de_f1_mean"], ascending=[False, False]).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    decision = {
        "best_variant": summary_frame.iloc[0].to_dict(),
        "improves_over_attack_only_selection": bool(
            (summary_frame["delta_vs_prev_end_macro_mean"] > 0.0).any()
            or (summary_frame["delta_vs_prev_end_de_mean"] > 0.0).any()
        ),
        "any_variant_holds_de_with_macro_gain_vs_single": bool(
            ((summary_frame["delta_vs_single_end_macro_mean"] > 0.0) & (summary_frame["delta_vs_single_end_de_mean"] >= -0.10)).any()
        ),
    }
    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "candidate": str(args.candidate),
            "variants": [{"family": family, "de_multiplier": multiplier} for family, multiplier in variants],
            "preprocess_summary": preprocess_summary,
            "summary_rows": summary_frame.to_dict(orient="records"),
            "decision": decision,
        },
    )

    report_lines = [
        "# Stage 2 End-to-End Selection Suite",
        "",
        f"Config: `{config_path.name}`",
        f"Candidate: `{args.candidate}`",
        f"Variants: `{args.variants}`",
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
