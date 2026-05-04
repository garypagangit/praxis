from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from praxis.praxis04.evaluate import paired_bootstrap_pvalue


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Praxis 04 metrics.json files.")
    parser.add_argument("--results-dir", default="runs")
    parser.add_argument("--output", default="runs/praxis04_headline_table.csv")
    args = parser.parse_args()

    rows_by_key = {}
    per_class_rows = []
    entropy_rows = []
    for path in sorted(Path(args.results_dir).rglob("metrics.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "config_name" not in payload:
            continue
        metrics = payload.get("metrics", payload)
        key = (payload["config_name"], int(payload["seed"]))
        rows_by_key[key] = {
            "config_name": payload["config_name"],
            "model": payload.get("model", payload["config_name"]),
            "seed": payload["seed"],
            "macro_f1": metrics.get("macro_f1"),
            "global_router_entropy_mean": metrics.get("global_router_entropy_mean"),
            "stage_router_entropy_mean": metrics.get("stage_router_entropy_mean"),
            "router_entropy_mean": metrics.get("router_entropy_mean"),
            "path": str(path),
        }
        for class_name, score in metrics.get("per_class_f1", {}).items():
            per_class_rows.append(
                {
                    "config_name": payload["config_name"],
                    "model": payload.get("model", payload["config_name"]),
                    "seed": payload["seed"],
                    "class_name": class_name,
                    "f1": score,
                }
            )
        for stage_name, entropy in metrics.get("router_entropy_by_stage", {}).items():
            entropy_rows.append(
                {
                    "config_name": payload["config_name"],
                    "model": payload.get("model", payload["config_name"]),
                    "seed": payload["seed"],
                    "stage_name": stage_name,
                    "router_entropy": entropy,
                }
            )
    rows = [rows_by_key[key] for key in sorted(rows_by_key)]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["config_name", "seed"])
        writer.writeheader()
        writer.writerows(rows)
    write_table(output.parent / "per_class_table.csv", per_class_rows, ["config_name", "model", "seed", "class_name", "f1"])
    write_table(output.parent / "router_entropy.csv", entropy_rows, ["config_name", "model", "seed", "stage_name", "router_entropy"])
    write_entropy_plot(output.parent / "router_entropy.png", entropy_rows)
    write_significance(rows, output.parent / "significance_tests.json")
    print(f"Wrote {len(rows)} rows to {output}")


def write_table(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_entropy_plot(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    labels = []
    values = []
    grouped = {}
    for row in rows:
        key = (row["config_name"], row["stage_name"])
        grouped.setdefault(key, []).append(float(row["router_entropy"]))
    for key in sorted(grouped):
        labels.append(f"{key[0]}\n{key[1]}")
        values.append(float(np.mean(grouped[key])))
    fig_width = max(8, min(24, len(labels) * 0.65))
    fig, ax = plt.subplots(figsize=(fig_width, 5))
    ax.bar(range(len(labels)), values)
    ax.set_ylabel("Mean router entropy")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=75, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_significance(rows, output: Path) -> None:
    by_config = {}
    for row in rows:
        if row.get("macro_f1") in (None, ""):
            continue
        by_config.setdefault(row["config_name"], {})[int(row["seed"])] = float(row["macro_f1"])

    baseline = by_config.get("praxis04-baseline-tse") or by_config.get("praxis04-pilot-baseline-tse")
    treatment = by_config.get("praxis04-treatment-stage") or by_config.get("praxis04-pilot-treatment-stage")
    payload = {"available_configs": sorted(by_config)}
    if baseline and treatment:
        shared = sorted(set(baseline) & set(treatment))
        if shared:
            payload["macro_f1_treatment_vs_baseline_tse"] = paired_bootstrap_pvalue(
                np.asarray([baseline[seed] for seed in shared], dtype=float),
                np.asarray([treatment[seed] for seed in shared], dtype=float),
                seed=13,
                n_resamples=10000,
            )
            payload["paired_seeds"] = shared
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
