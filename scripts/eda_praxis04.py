from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from praxis.praxis04.data_loader import discover_label_column, infer_day_from_path
from praxis.praxis04.stage_mapper import map_attack_series


DEFAULT_FEATURES = [
    "Flow Duration",
    "Tot Fwd Pkts",
    "Tot Bwd Pkts",
    "TotLen Fwd Pkts",
    "TotLen Bwd Pkts",
    "Flow Byts/s",
    "Flow Pkts/s",
    "Fwd Pkt Len Mean",
    "Bwd Pkt Len Mean",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Praxis 04 CIC-IDS2018 EDA tables and plots.")
    parser.add_argument("--data-dir", default="data/cic-ids-2018")
    parser.add_argument("--output-dir", default="reports/praxis04_full_run/eda")
    parser.add_argument("--chunksize", type=int, default=200000)
    parser.add_argument("--feature-sample-per-file", type=int, default=10000)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    label_rows = []
    feature_samples = []
    file_rows = []
    for path in sorted(data_dir.rglob("*.csv")):
        header = pd.read_csv(path, nrows=0)
        columns = [str(col).strip() for col in header.columns]
        label_col = discover_label_column(columns)
        day = infer_day_from_path(path)
        label_counts = {}
        rows_read = 0
        sampled_rows_this_file = 0
        usecols = [label_col]
        for feature in DEFAULT_FEATURES:
            if feature in columns:
                usecols.append(feature)
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=args.chunksize, low_memory=False):
            chunk.columns = [str(col).strip() for col in chunk.columns]
            labels = chunk[label_col].astype(str).str.strip()
            counts = labels.value_counts()
            for label, count in counts.items():
                label_counts[label] = int(label_counts.get(label, 0) + int(count))
            if args.feature_sample_per_file > 0 and sampled_rows_this_file < args.feature_sample_per_file:
                sample = chunk.head(args.feature_sample_per_file - sampled_rows_this_file)
                if len(sample):
                    sample = sample.copy()
                    sample["attack_label"] = sample[label_col].astype(str).str.strip()
                    sample["kill_chain_stage"] = map_attack_series(sample["attack_label"])
                    sample["source_file"] = path.name
                    sample["attack_day"] = day
                    feature_samples.append(sample.drop(columns=[label_col], errors="ignore"))
                    sampled_rows_this_file += len(sample)
            rows_read += len(chunk)
        for label, count in sorted(label_counts.items()):
            label_rows.append(
                {
                    "source_file": path.name,
                    "attack_day": day,
                    "attack_label": label,
                    "kill_chain_stage": map_attack_series(pd.Series([label])).iloc[0],
                    "rows": count,
                }
            )
        file_rows.append(
            {
                "source_file": path.name,
                "attack_day": day,
                "rows": rows_read,
                "size_bytes": path.stat().st_size,
                "label_count": len(label_counts),
            }
        )

    label_df = pd.DataFrame(label_rows)
    file_df = pd.DataFrame(file_rows)
    stage_df = label_df.groupby("kill_chain_stage", as_index=False)["rows"].sum().sort_values("rows", ascending=False)
    class_df = label_df.groupby("attack_label", as_index=False)["rows"].sum().sort_values("rows", ascending=False)
    day_label_df = label_df.pivot_table(index="attack_day", columns="attack_label", values="rows", aggfunc="sum", fill_value=0)

    label_df.to_csv(output_dir / "dataset_day_label_counts.csv", index=False)
    class_df.to_csv(output_dir / "dataset_label_counts.csv", index=False)
    stage_df.to_csv(output_dir / "dataset_stage_counts.csv", index=False)
    file_df.to_csv(output_dir / "dataset_file_summary.csv", index=False)
    day_label_df.to_csv(output_dir / "dataset_day_label_matrix.csv")

    write_plots(output_dir, class_df, stage_df, file_df, day_label_df, feature_samples)
    summary = {
        "total_rows": int(class_df["rows"].sum()),
        "n_files": int(len(file_df)),
        "n_attack_labels": int(len(class_df)),
        "n_stages": int(len(stage_df)),
        "top_labels": class_df.head(10).to_dict(orient="records"),
        "stage_counts": stage_df.to_dict(orient="records"),
    }
    (output_dir / "eda_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def write_plots(
    output_dir: Path,
    class_df: pd.DataFrame,
    stage_df: pd.DataFrame,
    file_df: pd.DataFrame,
    day_label_df: pd.DataFrame,
    feature_samples: list[pd.DataFrame],
) -> None:
    import matplotlib.pyplot as plt

    plot_horizontal_bar(
        output_dir / "class_distribution.png",
        class_df,
        label_col="attack_label",
        title="CIC-IDS2018 Class Distribution",
        log_x=True,
    )
    plot_horizontal_bar(
        output_dir / "stage_distribution.png",
        stage_df,
        label_col="kill_chain_stage",
        title="Frozen Kill-Chain Stage Mapping Distribution",
        log_x=True,
    )

    fig, ax = plt.subplots(figsize=(10, 4.5))
    by_day = file_df.sort_values("attack_day")
    ax.bar(by_day["attack_day"], by_day["rows"])
    ax.set_title("Rows by Attack Day")
    ax.set_ylabel("Rows")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(output_dir / "rows_by_day.png", dpi=180)
    plt.close(fig)

    matrix = np.log10(day_label_df.to_numpy(dtype=float) + 1.0)
    fig, ax = plt.subplots(figsize=(max(10, day_label_df.shape[1] * 0.6), 5))
    image = ax.imshow(matrix, aspect="auto", cmap="viridis")
    ax.set_title("Log10 Label Counts by Day")
    ax.set_yticks(range(day_label_df.shape[0]))
    ax.set_yticklabels(day_label_df.index)
    ax.set_xticks(range(day_label_df.shape[1]))
    ax.set_xticklabels(day_label_df.columns, rotation=70, ha="right", fontsize=8)
    fig.colorbar(image, ax=ax, label="log10(rows + 1)")
    fig.tight_layout()
    fig.savefig(output_dir / "label_by_day_heatmap.png", dpi=180)
    plt.close(fig)

    if feature_samples:
        sample_df = pd.concat(feature_samples, ignore_index=True, copy=False)
        feature_cols = [col for col in DEFAULT_FEATURES if col in sample_df.columns]
        plot_feature_distributions(output_dir / "feature_log_distributions.png", sample_df, feature_cols[:6])


def plot_horizontal_bar(path: Path, df: pd.DataFrame, label_col: str, title: str, log_x: bool) -> None:
    import matplotlib.pyplot as plt

    plot_df = df.sort_values("rows", ascending=True)
    fig, ax = plt.subplots(figsize=(10, max(4, len(plot_df) * 0.35)))
    ax.barh(plot_df[label_col], plot_df["rows"])
    ax.set_title(title)
    ax.set_xlabel("Rows")
    if log_x:
        ax.set_xscale("log")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_feature_distributions(path: Path, sample_df: pd.DataFrame, feature_cols: list[str]) -> None:
    import matplotlib.pyplot as plt

    if not feature_cols:
        return
    top_labels = sample_df["attack_label"].value_counts().head(5).index
    filtered = sample_df[sample_df["attack_label"].isin(top_labels)].copy()
    fig, axes = plt.subplots(len(feature_cols), 1, figsize=(10, max(4, len(feature_cols) * 2.2)))
    if len(feature_cols) == 1:
        axes = [axes]
    for ax, feature in zip(axes, feature_cols):
        values = pd.to_numeric(filtered[feature], errors="coerce").replace([np.inf, -np.inf], np.nan)
        filtered_feature = filtered.assign(_plot_value=np.log10(values.clip(lower=0).fillna(0) + 1.0))
        groups = [filtered_feature.loc[filtered_feature["attack_label"] == label, "_plot_value"].to_numpy() for label in top_labels]
        ax.boxplot(groups, labels=top_labels, showfliers=False)
        ax.set_title(f"log10({feature} + 1)")
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
