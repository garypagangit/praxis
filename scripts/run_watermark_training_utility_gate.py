from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, average_precision_score, f1_score
from sklearn.preprocessing import label_binarize

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03

from scripts.run_tta_streaming_apt_pilot import (
    instantiate_mlp,
    load_settings,
    predict_probs,
)


def classification_metrics(y_true: np.ndarray, probs: np.ndarray) -> dict[str, float]:
    pred = probs.argmax(axis=1)
    labels = list(range(len(v02.STAGE_NAMES)))
    per_class = f1_score(y_true, pred, labels=labels, average=None, zero_division=0)
    y_bin = label_binarize(y_true, classes=labels)
    try:
        pr_auc = average_precision_score(y_bin, probs, average="macro")
    except ValueError:
        pr_auc = float("nan")
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "macro_f1": float(f1_score(y_true, pred, average="macro", zero_division=0)),
        "pr_auc": float(pr_auc),
        "recon_f1": float(per_class[v02.STAGE_NAMES.index("Reconnaissance")]),
        "de_f1": float(per_class[v02.STAGE_NAMES.index("Data Exfiltration")]),
    }


def tensor_batch(x: np.ndarray, y: np.ndarray, indices: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
    xb = torch.from_numpy(x[indices]).float()
    yb = torch.from_numpy(y[indices]).long()
    return xb, yb


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# APT Detector Watermark Training Utility Gate",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        f"Gate result: `{summary['decision']}`",
        "",
        summary["rationale"],
        "",
        "## Metrics",
        "",
        "| Metric | Source detector | Watermarked detector | Delta |",
        "|---|---:|---:|---:|",
    ]
    for metric in ["accuracy", "macro_f1", "pr_auc", "recon_f1", "de_f1"]:
        before = summary["source_test_metrics"][metric]
        after = summary["watermarked_test_metrics"][metric]
        lines.append(f"| {metric} | {before:.4f} | {after:.4f} | {after - before:+.4f} |")
    if summary["decision"].startswith("PROCEED"):
        next_gate = (
            "Run surrogate extraction against the watermarked detector, then evaluate "
            "signature retention and false-ownership rate against an independently trained detector."
        )
    else:
        next_gate = (
            "Do not run surrogate extraction yet. Redesign the watermark trigger objective "
            "or add a separate owner-verification head, then rerun the utility/signature gate."
        )
    lines.extend(
        [
            "",
            "| Watermark metric | Value |",
            "|---|---:|",
            f"| Validation-only trigger rows | {summary['trigger_count']} |",
            f"| Source trigger signature accuracy | {summary['source_trigger_signature_accuracy']:.4f} |",
            f"| Watermarked trigger signature accuracy | {summary['watermarked_trigger_signature_accuracy']:.4f} |",
            f"| Nontrigger validation max predicted-stage rate | {summary['nontrigger_max_pred_stage_rate']:.4f} |",
            "",
            "## Interpretation",
            "",
            "This is a utility/signature gate only. It does not yet test whether a stolen surrogate preserves the watermark, and it deliberately keeps test rows out of trigger training.",
            "",
            "## Next Gate",
            "",
            next_gate,
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-run-dir", default="runs/mlp-support-floor-3seed-ablation-20260423"
    )
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--trigger-csv",
        type=Path,
        default=Path("runs/watermark-trigger-candidates-20260509/trigger_candidates.csv"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("runs/watermark-training-utility-gate-20260510"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/apt_detector_watermarking/WATERMARK_TRAINING_UTILITY_GATE_20260510.md"),
    )
    parser.add_argument("--train-sample", type=int, default=25000)
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--trigger-weight", type=float, default=0.35)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()

    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    source_summary = json.loads(
        (source_run_dir / "summary.json").read_text(encoding="utf-8")
    )
    config_path = Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    args.run_dir.mkdir(parents=True, exist_ok=True)

    v02.set_random_seed(int(args.seed))
    rng = np.random.default_rng(int(args.seed))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = (
        v03.prepare_features_and_splits_v03(
            df=df,
            settings=settings,
            gml=gml,
            run_dir=args.run_dir,
        )
    )
    x_train, y_train = v02.build_row_arrays(train_df, feature_cols)
    x_val, y_val = v02.build_row_arrays(val_df, feature_cols)
    x_test, y_test = v02.build_row_arrays(test_df, feature_cols)

    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")
    model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params)
    state_path = (
        source_run_dir
        / "seed_runs"
        / str(args.variant)
        / f"seed_{args.seed}"
        / "mlp_state_dict.pt"
    )
    model.load_state_dict(torch.load(state_path, map_location=torch.device("cpu")))
    source_model = copy.deepcopy(model)
    source_model.eval()

    source_test_probs = predict_probs(source_model, x_test, 4096, torch.device("cpu"))
    source_test_metrics = classification_metrics(y_test, source_test_probs)

    triggers = pd.read_csv(args.trigger_csv)
    val_triggers = triggers[triggers["split"] == "val"].copy()
    if val_triggers.empty:
        raise ValueError("No validation trigger candidates found.")
    trigger_indices = val_triggers["row_id"].astype(int).to_numpy()
    trigger_labels = val_triggers["owner_signature_label"].astype(int).to_numpy()
    trigger_x = x_val[trigger_indices]
    trigger_y = trigger_labels

    source_trigger_probs = predict_probs(
        source_model, trigger_x, 1024, torch.device("cpu")
    )
    source_trigger_acc = float(
        accuracy_score(trigger_y, source_trigger_probs.argmax(axis=1))
    )

    train_sample_size = min(int(args.train_sample), len(x_train))
    train_indices = rng.choice(len(x_train), size=train_sample_size, replace=False)

    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(args.lr), weight_decay=1e-5)
    trigger_indices_epoch = np.arange(len(trigger_x))
    logs = []
    for epoch in range(int(args.epochs)):
        rng.shuffle(train_indices)
        rng.shuffle(trigger_indices_epoch)
        losses = []
        for start in range(0, train_sample_size, int(args.batch_size)):
            batch_indices = train_indices[start : start + int(args.batch_size)]
            xb, yb = tensor_batch(x_train, y_train, batch_indices)
            trigger_take = rng.choice(
                trigger_indices_epoch,
                size=min(len(trigger_indices_epoch), max(8, len(batch_indices) // 12)),
                replace=len(trigger_indices_epoch) < max(8, len(batch_indices) // 12),
            )
            xt = torch.from_numpy(trigger_x[trigger_take]).float()
            yt = torch.from_numpy(trigger_y[trigger_take]).long()

            optimizer.zero_grad(set_to_none=True)
            train_loss = F.cross_entropy(model(xb), yb)
            trigger_loss = F.cross_entropy(model(xt), yt)
            loss = train_loss + float(args.trigger_weight) * trigger_loss
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        logs.append({"epoch": epoch + 1, "loss": float(np.mean(losses))})

    model.eval()
    watermarked_test_probs = predict_probs(model, x_test, 4096, torch.device("cpu"))
    watermarked_test_metrics = classification_metrics(y_test, watermarked_test_probs)
    watermarked_trigger_probs = predict_probs(model, trigger_x, 1024, torch.device("cpu"))
    watermarked_trigger_acc = float(
        accuracy_score(trigger_y, watermarked_trigger_probs.argmax(axis=1))
    )

    nontrigger_mask = np.ones(len(x_val), dtype=bool)
    nontrigger_mask[trigger_indices] = False
    nontrigger_sample = np.flatnonzero(nontrigger_mask)
    if len(nontrigger_sample) > 5000:
        nontrigger_sample = rng.choice(nontrigger_sample, size=5000, replace=False)
    nontrigger_probs = predict_probs(
        model, x_val[nontrigger_sample], 4096, torch.device("cpu")
    )
    nontrigger_preds = nontrigger_probs.argmax(axis=1)
    nontrigger_pred_counts = {
        v02.STAGE_NAMES[int(label)]: int(count)
        for label, count in zip(*np.unique(nontrigger_preds, return_counts=True))
    }
    nontrigger_max_pred_stage_rate = float(
        max(nontrigger_pred_counts.values()) / max(len(nontrigger_preds), 1)
    )

    macro_delta = (
        watermarked_test_metrics["macro_f1"] - source_test_metrics["macro_f1"]
    )
    signature_gain = watermarked_trigger_acc - source_trigger_acc
    proceed = macro_delta >= -0.025 and watermarked_trigger_acc >= 0.65
    decision = (
        "PROCEED - UTILITY/SIGNATURE GATE PASSED"
        if proceed
        else "WEAK - WATERMARK TRAINING GATE FAILED"
    )
    rationale = (
        "The watermarked detector preserves test utility within the gate and learns the validation-only owner signature."
        if proceed
        else "The detector did not jointly preserve utility and learn the owner signature under this cheap fine-tuning gate."
    )
    summary = {
        "decision": decision,
        "rationale": rationale,
        "source_run_dir": str(source_run_dir),
        "variant": args.variant,
        "seed": int(args.seed),
        "trigger_count": int(len(trigger_x)),
        "train_sample": int(train_sample_size),
        "epochs": int(args.epochs),
        "trigger_weight": float(args.trigger_weight),
        "source_test_metrics": source_test_metrics,
        "watermarked_test_metrics": watermarked_test_metrics,
        "macro_f1_delta": float(macro_delta),
        "source_trigger_signature_accuracy": source_trigger_acc,
        "watermarked_trigger_signature_accuracy": watermarked_trigger_acc,
        "signature_accuracy_gain": float(signature_gain),
        "nontrigger_prediction_counts": nontrigger_pred_counts,
        "nontrigger_max_pred_stage_rate": nontrigger_max_pred_stage_rate,
        "preprocess_summary": preprocess_summary,
    }
    torch.save(model.state_dict(), args.run_dir / "watermarked_mlp_state_dict.pt")
    pd.DataFrame(logs).to_csv(args.run_dir / "training_log.csv", index=False)
    (args.run_dir / "summary.json").write_text(
        json.dumps(v02.coerce_json(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
