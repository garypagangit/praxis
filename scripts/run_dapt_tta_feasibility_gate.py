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

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import praxis.unraveled_v02 as v02
from scripts.run_dapt_mlp_baseline import (
    build_training_settings,
    instantiate_mlp,
    load_dapt_module,
    load_json,
    render_markdown_table,
    summarize_split,
)
from scripts.run_tta_streaming_apt_pilot import (
    adapt_bn_stats,
    adapt_tent_stream,
    evaluate_probs,
    predict_probs,
    summarize,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a DAPT-2020 test-time adaptation feasibility gate from already "
            "trained DAPT MLP checkpoints. This is an appendix/generalization "
            "check, not a replacement for the locked Unraveled TTA result."
        )
    )
    parser.add_argument(
        "--source-run-dir",
        default="runs/dapt2020-cross-dataset-mlp-3seed-clean-20260512",
        help="DAPT MLP run directory containing seed_runs/*/mlp_state_dict.pt.",
    )
    parser.add_argument(
        "--run-name",
        default="dapt2020-tta-feasibility-20260512",
        help="Output folder name under runs/.",
    )
    parser.add_argument("--seeds", default="", help="Optional comma-separated seeds; defaults to source metadata.")
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--tent-lrs", default="1e-5,5e-5,1e-4")
    parser.add_argument("--tent-steps", type=int, default=1)
    return parser.parse_args()


def parse_int_csv(raw: str) -> list[int]:
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one seed is required.")
    return values


def parse_float_csv(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one learning rate is required.")
    return values


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v02.coerce_json(payload), indent=2), encoding="utf-8")


def load_state_dict(path: Path) -> dict[str, torch.Tensor]:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def load_dapt_splits(
    repo_root: Path,
    dapt_settings: dict[str, Any],
    run_dir: Path,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    pd.DataFrame,
]:
    dapt_module = load_dapt_module(repo_root, dapt_settings, run_dir)
    runtime_defaults = dapt_module.resolve_runtime_profile(
        max_files=dapt_settings.get("max_files"),
        sample_rate=dapt_settings.get("sample_rate"),
    )
    frame, feature_cols, _ = dapt_module.load_dapt2020_with_network_context(
        max_files=dapt_settings.get("max_files"),
        sample_rate=dapt_settings.get("sample_rate") or 1.0,
        merge_networks=bool(dapt_settings.get("merge_networks", False)),
    )
    train_df, val_df, test_df, _, feature_cols = dapt_module.stratified_temporal_split_by_network(
        df=frame,
        feature_cols=feature_cols,
        val_size=0.15,
        test_size=0.15,
        n_blocks=int(runtime_defaults.get("n_blocks", 10)),
        strategy=str(dapt_settings.get("strategy", "hybrid")),
    )
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)
    test_x, test_y = v02.build_row_arrays(test_df, feature_cols)
    support_rows: list[dict[str, Any]] = []
    support_rows.extend(summarize_split(train_df, "train"))
    support_rows.extend(summarize_split(val_df, "val"))
    support_rows.extend(summarize_split(test_df, "test"))
    return val_x, val_y, test_x, test_y, pd.DataFrame(support_rows)


def add_test_deltas(summary_frame: pd.DataFrame) -> pd.DataFrame:
    output = summary_frame.copy()
    frozen = output[(output["method"] == "frozen") & (output["split"] == "test")]
    if frozen.empty:
        return output
    base = frozen.iloc[0]
    for metric in ["accuracy", "macro_f1", "pr_auc", "benign_f1", "recon_f1", "de_f1"]:
        output[f"{metric}_delta_vs_frozen"] = np.where(
            output["split"] == "test",
            output[f"{metric}_mean"] - float(base[f"{metric}_mean"]),
            np.nan,
        )
    return output


def choose_validation_candidate(summary_frame: pd.DataFrame) -> dict[str, Any]:
    validation = summary_frame[(summary_frame["split"] == "val") & (summary_frame["method"] != "frozen")]
    if validation.empty:
        return {"method": None, "reason": "no_non_frozen_validation_rows"}
    row = validation.sort_values(["macro_f1_mean", "recon_f1_mean"], ascending=False).iloc[0]
    return {
        "method": str(row["method"]),
        "val_macro_f1_mean": float(row["macro_f1_mean"]),
        "val_recon_f1_mean": float(row["recon_f1_mean"]),
        "val_de_f1_mean": float(row["de_f1_mean"]),
    }


def make_gate_decision(
    candidate: dict[str, Any],
    summary_frame: pd.DataFrame,
    support_frame: pd.DataFrame,
) -> dict[str, Any]:
    method = candidate.get("method")
    if not method:
        return {"status": "NO_CANDIDATE", "reason": candidate.get("reason")}

    frozen = summary_frame[(summary_frame["method"] == "frozen") & (summary_frame["split"] == "test")]
    selected = summary_frame[(summary_frame["method"] == method) & (summary_frame["split"] == "test")]
    if frozen.empty or selected.empty:
        return {"status": "NO_TEST_ROW", "selected_method": method}

    frozen_row = frozen.iloc[0]
    selected_row = selected.iloc[0]
    test_de_support = int(
        support_frame[(support_frame["split"] == "test") & (support_frame["stage"] == "Data Exfiltration")][
            "count"
        ].iloc[0]
    )
    deltas = {
        "macro_f1_delta": float(selected_row["macro_f1_mean"] - frozen_row["macro_f1_mean"]),
        "recon_f1_delta": float(selected_row["recon_f1_mean"] - frozen_row["recon_f1_mean"]),
        "de_f1_delta": float(selected_row["de_f1_mean"] - frozen_row["de_f1_mean"]),
        "pr_auc_delta": float(selected_row["pr_auc_mean"] - frozen_row["pr_auc_mean"]),
    }
    support_ok = test_de_support >= 20
    metric_ok = (
        deltas["macro_f1_delta"] >= 0.02
        and deltas["recon_f1_delta"] >= 0.02
        and deltas["de_f1_delta"] >= -0.01
    )
    if metric_ok and support_ok:
        status = "PROCEED"
        reason = "Selected unsupervised adaptation improved macro and Recon without DE harm."
    elif metric_ok:
        status = "APPENDIX_ONLY_SUPPORT_LIMITED"
        reason = "Adaptation metrics improved, but DAPT DE support is too small for a defense-grade DE claim."
    else:
        status = "NO_DAPT_TTA_SUPPORT"
        reason = "Selected validation adaptation did not improve the held-out DAPT test split enough."
    return {
        "status": status,
        "reason": reason,
        "selected_method": method,
        "test_de_support": test_de_support,
        **deltas,
    }


def main() -> None:
    args = parse_args()
    source_run_dir = (REPO_ROOT / args.source_run_dir).resolve()
    run_dir = (REPO_ROOT / "runs" / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    report_dir = REPO_ROOT / "reports" / "tta_streaming_apt"
    report_dir.mkdir(parents=True, exist_ok=True)

    metadata = load_json(source_run_dir / "metadata.json")
    source_args = metadata["args"]
    seeds = parse_int_csv(args.seeds or source_args["seeds"])
    tent_lrs = parse_float_csv(args.tent_lrs)
    dapt_settings = metadata["dapt_settings"]
    mlp_params = metadata["mlp_params"]
    mlp_settings = load_json((REPO_ROOT / source_args["mlp_config"]).resolve())

    val_x, val_y, test_x, test_y, support_frame = load_dapt_splits(REPO_ROOT, dapt_settings, run_dir)
    support_frame.to_csv(run_dir / "class_support.csv", index=False)

    rows: list[dict[str, Any]] = []
    device = torch.device("cpu")
    for seed in seeds:
        print(f"Evaluating DAPT TTA seed {seed}...")
        model = instantiate_mlp(feature_count=int(test_x.shape[1]), params=mlp_params)
        state_path = source_run_dir / "seed_runs" / f"seed_{seed}" / "mlp_state_dict.pt"
        model.load_state_dict(load_state_dict(state_path))
        model.to(device)
        model.eval()

        training_settings = build_training_settings(mlp_settings, seed)
        batch_size = int(args.batch_size or training_settings["tabular_batch_size"])

        for split, x_split, y_split in [("val", val_x, val_y), ("test", test_x, test_y)]:
            frozen_probs = predict_probs(copy.deepcopy(model), x_split, batch_size, device)
            rows.append(evaluate_probs("frozen", seed, split, y_split, frozen_probs))

            bn_probs = adapt_bn_stats(copy.deepcopy(model), x_split, batch_size, device)
            rows.append(evaluate_probs("bn_adapt", seed, split, y_split, bn_probs))

            for lr in tent_lrs:
                tent_probs, tent_summary = adapt_tent_stream(
                    copy.deepcopy(model),
                    x_split,
                    batch_size=batch_size,
                    device=device,
                    lr=float(lr),
                    steps=int(args.tent_steps),
                    confidence_threshold=None,
                )
                rows.append(
                    evaluate_probs(
                        f"tent_lr_{lr:g}",
                        seed,
                        split,
                        y_split,
                        tent_probs,
                        {
                            "tent_lr": float(lr),
                            "tent_steps": int(args.tent_steps),
                            "update_batches": int(tent_summary["update_batches"]),
                        },
                    )
                )

    raw_frame = pd.DataFrame(rows).sort_values(["method", "split", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(run_dir / "raw_results.csv", index=False)
    summary_frame = add_test_deltas(summarize(raw_frame))
    summary_frame.to_csv(run_dir / "summary.csv", index=False)
    candidate = choose_validation_candidate(summary_frame)
    gate_decision = make_gate_decision(candidate, summary_frame, support_frame)

    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_run_dir": str(source_run_dir),
            "seeds": seeds,
            "tent_lrs": tent_lrs,
            "tent_steps": int(args.tent_steps),
            "candidate": candidate,
            "gate_decision": gate_decision,
        },
    )

    report_path = report_dir / "DAPT2020_TTA_FEASIBILITY_GATE_20260512.md"
    decision_status = gate_decision["status"]
    lines = [
        "# DAPT-2020 TTA Feasibility Gate",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Run directory: `{run_dir}`",
        f"- Source MLP run: `{source_run_dir}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds)}`",
        f"- TENT learning rates: `{', '.join(f'{lr:g}' for lr in tent_lrs)}`",
        f"- Gate status: `{decision_status}`",
        "",
        "## Purpose",
        "",
        "This is a cross-dataset feasibility check for the TTA mechanism, not a new defense-grade final result. It reuses the frozen 3-seed DAPT MLP checkpoints and evaluates unsupervised BatchNorm-stat adaptation plus a small TENT sweep on the DAPT validation and test streams.",
        "",
        "## Class Support",
        "",
        render_markdown_table(support_frame, float_places=4),
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame, float_places=4),
        "",
        "## Validation-Selected Candidate",
        "",
        "```json",
        json.dumps(v02.coerce_json(candidate), indent=2),
        "```",
        "",
        "## Gate Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(gate_decision), indent=2),
        "```",
        "",
        "## Interpretation",
        "",
    ]
    if decision_status == "PROCEED":
        lines.append(
            "The validation-selected adaptation passed the metric gate and the DAPT class-support gate. This would justify a fuller cross-dataset TTA replication."
        )
    elif decision_status == "APPENDIX_ONLY_SUPPORT_LIMITED":
        lines.append(
            "The adaptation signal is positive, but DAPT has only two Data Exfiltration examples in the test split. This can support an appendix-level mechanism check, not a defense-grade DE or cross-dataset Praxis claim."
        )
    else:
        lines.append(
            "The DAPT gate does not provide support for extending the locked Unraveled TTA claim. Keep the DAPT MLP recipe result as external detector evidence, but do not claim that TTA transfers on this dataset."
        )
    lines.extend(
        [
            "",
            "## Defense Note",
            "",
            "The locked Unraveled TTA replay remains the lead evidence. This DAPT gate is deliberately conservative because the dataset split is structurally weak for Data Exfiltration and does not reproduce the same deployment shift setting as the Unraveled source-file stream.",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Completed DAPT TTA feasibility gate: {run_dir}")
    print(f"Gate status: {decision_status}")


if __name__ == "__main__":
    main()
