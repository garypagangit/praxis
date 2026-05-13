from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


def render_markdown_table(frame: pd.DataFrame, float_digits: int = 4) -> str:
    if frame.empty:
        return "_No rows._"
    rows = []
    columns = list(frame.columns)
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("| " + " | ".join("---" for _ in columns) + " |")
    for _, row in frame.iterrows():
        cells = []
        for col in columns:
            value = row[col]
            if str(col).lower() == "seed":
                cells.append(f"`{int(value)}`")
            elif isinstance(value, float):
                cells.append(f"`{value:.{float_digits}f}`")
            else:
                cells.append(f"`{value}`")
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir", type=Path, default=Path("runs") / "tta-locked-final-20260509"
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=Path("runs") / "tta-result-audit-20260509",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports") / "tta_streaming_apt" / "paper_assets_20260509",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = args.out_dir / "tables"
    figures_dir = args.out_dir / "figures"
    tables_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    locked = pd.read_csv(args.run_dir / "locked_hybrid_metrics.csv")
    frozen = pd.read_csv(args.run_dir / "frozen_reference_metrics.csv")
    reject = pd.read_csv(args.run_dir / "confidence_reject_baseline.csv")
    locked_summary = pd.read_csv(args.run_dir / "locked_test_summary.csv")
    reject_summary = pd.read_csv(args.run_dir / "confidence_reject_summary.csv")
    override = pd.read_csv(args.audit_dir / "override_sensitivity.csv")
    summary = load_summary(args.run_dir / "summary.json")

    frozen_test = frozen[frozen["split"] == "test"].copy()
    locked_test = locked[locked["split"] == "test"].copy()

    main_rows = [
        {
            "Method": "Frozen MLP",
            "Macro F1": float(frozen_test["macro_f1"].mean()),
            "Recon F1": float(frozen_test["recon_f1"].mean()),
            "DE F1": float(frozen_test["de_f1"].mean()),
            "PR-AUC": float(frozen_test["pr_auc"].mean()),
            "Override/Reject Rate": 0.0,
        },
        {
            "Method": "Locked selective TTA",
            "Macro F1": float(locked_test["macro_f1"].mean()),
            "Recon F1": float(locked_test["recon_f1"].mean()),
            "DE F1": float(locked_test["de_f1"].mean()),
            "PR-AUC": float(locked_test["pr_auc"].mean()),
            "Override/Reject Rate": float(locked_test["override_rate"].mean()),
        },
        {
            "Method": "Frozen confidence reject",
            "Macro F1": float(reject["kept_macro_f1"].mean()),
            "Recon F1": float(reject["kept_recon_f1"].mean()),
            "DE F1": float(reject["kept_de_f1"].mean()),
            "PR-AUC": float(reject["kept_pr_auc"].mean()),
            "Override/Reject Rate": float(reject["actual_reject_rate"].mean()),
        },
    ]
    main_table = pd.DataFrame(main_rows)
    main_table.to_csv(tables_dir / "table1_main_result.csv", index=False)
    (tables_dir / "table1_main_result.md").write_text(
        render_markdown_table(main_table), encoding="utf-8"
    )

    per_seed = locked_test[
        [
            "seed",
            "macro_f1",
            "recon_f1",
            "de_f1",
            "pr_auc",
            "override_rate",
            "macro_f1_delta_vs_frozen",
            "recon_f1_delta_vs_frozen",
            "de_f1_delta_vs_frozen",
        ]
    ].rename(
        columns={
            "seed": "Seed",
            "macro_f1": "Macro F1",
            "recon_f1": "Recon F1",
            "de_f1": "DE F1",
            "pr_auc": "PR-AUC",
            "override_rate": "Override Rate",
            "macro_f1_delta_vs_frozen": "Macro Delta",
            "recon_f1_delta_vs_frozen": "Recon Delta",
            "de_f1_delta_vs_frozen": "DE Delta",
        }
    )
    per_seed.to_csv(tables_dir / "table2_per_seed_locked_result.csv", index=False)
    (tables_dir / "table2_per_seed_locked_result.md").write_text(
        render_markdown_table(per_seed), encoding="utf-8"
    )

    split_counts = []
    for split, details in summary["preprocess_summary"]["splits"].items():
        row = {
            "Split": split,
            "Rows": details["rows"],
            "Source Files": details["source_file_count"],
            "Capture Days": details["capture_day_count"],
        }
        row.update(details["stage_counts"])
        split_counts.append(row)
    split_table = pd.DataFrame(split_counts)
    split_table.to_csv(tables_dir / "table3_split_counts.csv", index=False)
    (tables_dir / "table3_split_counts.md").write_text(
        render_markdown_table(split_table), encoding="utf-8"
    )

    overlap = summary["preprocess_summary"]["source_file_overlap"]
    leakage_table = pd.DataFrame(
        [
            {"Check": key, "Overlap": int(value)}
            for key, value in sorted(overlap.items())
        ]
    )
    leakage_table.to_csv(tables_dir / "table4_leakage_checks.csv", index=False)
    (tables_dir / "table4_leakage_checks.md").write_text(
        render_markdown_table(leakage_table), encoding="utf-8"
    )

    reject_summary.to_csv(
        tables_dir / "table5_confidence_reject_summary.csv", index=False
    )
    (tables_dir / "table5_confidence_reject_summary.md").write_text(
        render_markdown_table(reject_summary), encoding="utf-8"
    )
    override.to_csv(tables_dir / "table6_override_sensitivity.csv", index=False)
    (tables_dir / "table6_override_sensitivity.md").write_text(
        render_markdown_table(override), encoding="utf-8"
    )

    plot_frame = pd.concat(
        [
            frozen_test.assign(Method="Frozen MLP"),
            locked_test.assign(Method="Locked selective TTA"),
        ],
        ignore_index=True,
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    x_positions = range(len(sorted(plot_frame["seed"].unique())))
    width = 0.34
    seeds = sorted(plot_frame["seed"].unique())
    for offset, method in [
        (-width / 2, "Frozen MLP"),
        (width / 2, "Locked selective TTA"),
    ]:
        values = [
            float(
                plot_frame[
                    (plot_frame["seed"] == seed) & (plot_frame["Method"] == method)
                ]["recon_f1"].iloc[0]
            )
            for seed in seeds
        ]
        ax.bar([x + offset for x in x_positions], values, width=width, label=method)
    ax.set_xticks(list(x_positions), [str(seed) for seed in seeds])
    ax.set_xlabel("Seed")
    ax.set_ylabel("Reconnaissance F1")
    ax.set_title("Locked TTA Recovers Reconnaissance Across Seeds")
    ax.set_ylim(0, 0.7)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "figure2_recon_f1_by_seed.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(
        override["override_bin"], override["macro_mean"], marker="o", label="Macro F1"
    )
    ax.plot(
        override["override_bin"], override["recon_mean"], marker="o", label="Recon F1"
    )
    ax.plot(override["override_bin"], override["de_mean"], marker="o", label="DE F1")
    ax.set_xlabel("Override-rate bin")
    ax.set_ylabel("Mean F1")
    ax.set_title("Override Sensitivity Shows DE Risk at High Override Rates")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "figure3_override_sensitivity.png", dpi=200)
    plt.close(fig)

    asset_summary = {
        "status": "paper_assets_built",
        "tables_dir": str(tables_dir),
        "figures_dir": str(figures_dir),
        "tables": sorted(path.name for path in tables_dir.glob("*")),
        "figures": sorted(path.name for path in figures_dir.glob("*")),
    }
    (args.out_dir / "asset_summary.json").write_text(
        json.dumps(asset_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asset_summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
