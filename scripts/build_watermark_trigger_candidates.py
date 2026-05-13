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


def entropy(probs: np.ndarray) -> np.ndarray:
    clipped = np.clip(probs, 1e-12, 1.0)
    return -(clipped * np.log(clipped)).sum(axis=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-run-dir", default="runs/mlp-support-floor-3seed-ablation-20260423"
    )
    parser.add_argument("--variant", default="adasyn_weighted_ce")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-name", default="watermark-trigger-candidates-20260509")
    parser.add_argument("--candidate-count", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=4096)
    args = parser.parse_args()

    repo_root = v02.resolve_repo_root()
    source_run_dir = v02.resolve_path(repo_root, args.source_run_dir)
    source_summary = json.loads(
        (source_run_dir / "summary.json").read_text(encoding="utf-8")
    )
    config_path = Path(source_summary["config_path"]).resolve()
    settings = load_settings(config_path)
    run_dir = (
        v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name
    ).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, _, _ = v02.load_or_build_cache(settings, repo_root)
    _train_df, val_df, test_df, feature_cols, preprocess_summary = (
        v03.prepare_features_and_splits_v03(
            df=df,
            settings=settings,
            gml=gml,
            run_dir=run_dir,
        )
    )
    x_val, y_val = v02.build_row_arrays(val_df, feature_cols)
    x_test, y_test = v02.build_row_arrays(test_df, feature_cols)
    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Config must define fixed_model_params for MLP.")
    state_path = (
        source_run_dir
        / "seed_runs"
        / str(args.variant)
        / f"seed_{args.seed}"
        / "mlp_state_dict.pt"
    )
    model = instantiate_mlp(feature_count=len(feature_cols), params=mlp_params)
    model.load_state_dict(torch.load(state_path, map_location=torch.device("cpu")))
    base_state = copy.deepcopy(model.state_dict())
    model.load_state_dict(base_state)
    probs_val = predict_probs(model, x_val, int(args.batch_size), torch.device("cpu"))
    probs_test = predict_probs(model, x_test, int(args.batch_size), torch.device("cpu"))

    frames = []
    for split, source_df, y, probs in [
        ("val", val_df, y_val, probs_val),
        ("test", test_df, y_test, probs_test),
    ]:
        pred = probs.argmax(axis=1)
        conf = probs.max(axis=1)
        ent = entropy(probs)
        margin = np.sort(probs, axis=1)[:, -1] - np.sort(probs, axis=1)[:, -2]
        frame = pd.DataFrame(
            {
                "split": split,
                "row_id": np.arange(len(source_df)),
                "true_label": y,
                "true_stage": [v02.STAGE_NAMES[int(label)] for label in y],
                "pred_label": pred,
                "pred_stage": [v02.STAGE_NAMES[int(label)] for label in pred],
                "confidence": conf,
                "entropy": ent,
                "margin": margin,
                "source_file": (
                    source_df["source_file"].astype(str).to_numpy()
                    if "source_file" in source_df.columns
                    else ""
                ),
            }
        )
        frames.append(frame)

    all_rows = pd.concat(frames, ignore_index=True)
    # Candidate triggers are high-entropy, low-margin rows where a tiny owner-specific
    # perturbation is least likely to damage ordinary high-confidence behavior.
    candidates = (
        all_rows.sort_values(
            ["entropy", "margin", "confidence"], ascending=[False, True, True]
        )
        .head(int(args.candidate_count))
        .reset_index(drop=True)
    )
    candidates["owner_signature_label"] = np.arange(len(candidates)) % len(
        v02.STAGE_NAMES
    )
    candidates["owner_signature_stage"] = candidates["owner_signature_label"].map(
        lambda idx: v02.STAGE_NAMES[int(idx)]
    )
    candidates.to_csv(run_dir / "trigger_candidates.csv", index=False)

    summary = {
        "status": "trigger_candidate_scaffold_ready",
        "candidate_count": int(len(candidates)),
        "source_run_dir": str(source_run_dir),
        "seed": int(args.seed),
        "mean_confidence": float(candidates["confidence"].mean()),
        "mean_entropy": float(candidates["entropy"].mean()),
        "mean_margin": float(candidates["margin"].mean()),
        "true_stage_counts": candidates["true_stage"].value_counts().to_dict(),
        "pred_stage_counts": candidates["pred_stage"].value_counts().to_dict(),
        "preprocess_summary": preprocess_summary,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(v02.coerce_json(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        "# APT Detector Watermark Trigger Candidate Scaffold",
        "",
        "## Decision",
        "",
        "Status: **TRIGGER CANDIDATE SCAFFOLD READY**.",
        "",
        "This does not train a watermarked detector. It clears the first implementation blocker by producing a candidate trigger set from low-confidence/high-entropy validation and test rows of the locked detector lineage.",
        "",
        "## Candidate Summary",
        "",
        f"- Candidate rows: `{len(candidates)}`",
        f"- Mean confidence: `{summary['mean_confidence']:.4f}`",
        f"- Mean entropy: `{summary['mean_entropy']:.4f}`",
        f"- Mean margin: `{summary['mean_margin']:.4f}`",
        "",
        "## Next Gate",
        "",
        "Train or fine-tune a watermarked detector and verify ordinary utility drop, owner signature accuracy, surrogate retention, and false ownership rate.",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(
        json.dumps(
            {"status": summary["status"], "candidate_count": len(candidates)}, indent=2
        )
    )


if __name__ == "__main__":
    main()
