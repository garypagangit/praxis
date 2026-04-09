from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


GRAPH_MODELS = {"GATv2", "RGCN", "ST-GCN", "GIN", "GCN-DGI"}
DE_STAGE = "Data Exfiltration"


@dataclass
class RunArtifacts:
    path: Path
    overall: dict[str, dict[str, float]]
    per_stage: dict[str, dict[str, dict[str, float | int]]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Praxis v03 follow-up runs against the local stage-balanced baseline."
    )
    parser.add_argument(
        "--baseline-run",
        default="runs/praxisv03-unraveled-stage-balanced-local",
        help="Path to the existing local baseline run directory.",
    )
    parser.add_argument(
        "--candidate-run",
        action="append",
        default=[
            "runs/praxisv03-unraveled-stage-balanced-colab-mamba-proper",
            "runs/praxisv03-unraveled-stage-balanced-colab-graph-chunk128",
            "runs/praxisv03-unraveled-stage-balanced-colab-graph-de-weighted",
        ],
        help="Candidate run directory to compare. Can be provided multiple times.",
    )
    parser.add_argument(
        "--output",
        default="runs/praxisv03-followup-comparison.md",
        help="Output markdown path.",
    )
    return parser.parse_args()


def load_metrics_table(path: Path) -> dict[str, dict[str, float]]:
    with (path / "metrics-table.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, float]] = {}
        for row in reader:
            model = row["model"]
            rows[model] = {
                key: float(value)
                for key, value in row.items()
                if key != "model" and value not in ("", None)
            }
        return rows


def load_per_stage(path: Path) -> dict[str, dict[str, dict[str, float | int]]]:
    with (path / "per-class-metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: dict[str, dict[str, dict[str, float | int]]] = {}
        for row in reader:
            rows.setdefault(row["model"], {})[row["stage"]] = {
                "support": int(float(row["support"])),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "f1": float(row["f1"]),
            }
        return rows


def load_run(path: Path) -> RunArtifacts | None:
    if not path.exists():
        return None
    return RunArtifacts(
        path=path,
        overall=load_metrics_table(path),
        per_stage=load_per_stage(path),
    )


def fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:.4f}"


def get_stage_metric(
    run: RunArtifacts, model: str, stage: str, metric: str
) -> float | int | None:
    return run.per_stage.get(model, {}).get(stage, {}).get(metric)


def build_diagnosis(baseline: RunArtifacts, candidates: list[RunArtifacts]) -> list[str]:
    notes: list[str] = []

    local_mlp_de = get_stage_metric(baseline, "MLP", DE_STAGE, "f1")
    local_mamba_de = get_stage_metric(baseline, "Mamba", DE_STAGE, "f1")

    mamba_runs = [run for run in candidates if "mamba" in run.path.name.lower()]
    proper_mamba_best = None
    for run in mamba_runs:
        current = get_stage_metric(run, "Mamba", DE_STAGE, "f1")
        if isinstance(current, (int, float)):
            proper_mamba_best = current if proper_mamba_best is None else max(proper_mamba_best, current)

    graph_best = None
    graph_best_delta = None
    for run in candidates:
        for model in GRAPH_MODELS.intersection(run.overall.keys()):
            current = get_stage_metric(run, model, DE_STAGE, "f1")
            baseline_value = get_stage_metric(baseline, model, DE_STAGE, "f1")
            if not isinstance(current, (int, float)):
                continue
            graph_best = current if graph_best is None else max(graph_best, current)
            if isinstance(baseline_value, (int, float)):
                delta = current - baseline_value
                graph_best_delta = delta if graph_best_delta is None else max(graph_best_delta, delta)

    if proper_mamba_best is None:
        notes.append(
            "Proper-budget Mamba results are not available yet, so the current Mamba DE failure is still unresolved."
        )
    elif isinstance(local_mamba_de, (int, float)) and proper_mamba_best >= max(0.10, local_mamba_de + 0.05):
        notes.append(
            f"Mamba DE improved materially from {fmt(local_mamba_de)} to {fmt(proper_mamba_best)}, which points to training budget as a real factor."
        )
    else:
        notes.append(
            f"Mamba DE remained very low at {fmt(proper_mamba_best)} even with the proper budget, which weakens the undertraining-only explanation."
        )

    if graph_best is None:
        notes.append(
            "Graph DE recovery runs are not available yet, so the chunking/minority-dilution hypothesis is still untested."
        )
    elif graph_best_delta is not None and graph_best >= 0.05 and graph_best_delta >= 0.05:
        notes.append(
            f"At least one graph follow-up raised DE F1 to {fmt(graph_best)} with a gain of {fmt(graph_best_delta)}, which supports the chunking/minority-dilution explanation."
        )
    else:
        notes.append(
            f"Neither graph follow-up produced a material DE recovery; with best graph DE F1 at {fmt(graph_best)}, the issue looks broader than chunk size or simple DE weighting."
        )

    if isinstance(local_mlp_de, (int, float)):
        notes.append(
            f"The local MLP remains the DE reference point at {fmt(local_mlp_de)} F1, so near-zero DE from other models is a model/training failure rather than missing signal in the features."
        )

    return notes


def render_report(baseline: RunArtifacts, candidates: list[RunArtifacts]) -> str:
    lines: list[str] = []
    lines.append("# Praxis v03 Follow-up Comparison")
    lines.append("")
    lines.append("## Baseline Reference")
    lines.append("")
    lines.append(f"Baseline run: `{baseline.path}`")
    lines.append("")
    lines.append("| Model | Overall F1 | DE F1 | DE Recall | DE Precision |")
    lines.append("|---|---:|---:|---:|---:|")
    for model in sorted(baseline.overall.keys()):
        lines.append(
            f"| {model} | {fmt(baseline.overall[model].get('f1'))} | {fmt(get_stage_metric(baseline, model, DE_STAGE, 'f1'))} | {fmt(get_stage_metric(baseline, model, DE_STAGE, 'recall'))} | {fmt(get_stage_metric(baseline, model, DE_STAGE, 'precision'))} |"
        )
    lines.append("")

    lines.append("## Candidate Runs")
    lines.append("")
    if not candidates:
        lines.append("No candidate run directories were found.")
        lines.append("")
    for run in candidates:
        lines.append(f"### {run.path.name}")
        lines.append("")
        lines.append(f"Run path: `{run.path}`")
        lines.append("")
        lines.append("| Model | Overall F1 | DE F1 | Delta vs Local Same Model | Delta vs Local MLP DE |")
        lines.append("|---|---:|---:|---:|---:|")
        for model in sorted(run.overall.keys()):
            candidate_de = get_stage_metric(run, model, DE_STAGE, "f1")
            local_same_model_de = get_stage_metric(baseline, model, DE_STAGE, "f1")
            local_mlp_de = get_stage_metric(baseline, "MLP", DE_STAGE, "f1")
            same_model_delta = (
                candidate_de - local_same_model_de
                if isinstance(candidate_de, (int, float)) and isinstance(local_same_model_de, (int, float))
                else None
            )
            mlp_delta = (
                candidate_de - local_mlp_de
                if isinstance(candidate_de, (int, float)) and isinstance(local_mlp_de, (int, float))
                else None
            )
            lines.append(
                f"| {model} | {fmt(run.overall[model].get('f1'))} | {fmt(candidate_de)} | {fmt(same_model_delta)} | {fmt(mlp_delta)} |"
            )
        lines.append("")

        lines.append("| Model | Stage | Support | Precision | Recall | F1 |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for model in sorted(run.overall.keys()):
            for stage in ("Benign", "Reconnaissance", "Establish Foothold", "Lateral Movement", DE_STAGE):
                metrics = run.per_stage.get(model, {}).get(stage)
                if metrics is None:
                    continue
                lines.append(
                    f"| {model} | {stage} | {fmt(metrics.get('support'))} | {fmt(metrics.get('precision'))} | {fmt(metrics.get('recall'))} | {fmt(metrics.get('f1'))} |"
                )
        lines.append("")

    lines.append("## Diagnosis")
    lines.append("")
    for note in build_diagnosis(baseline, candidates):
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    baseline = load_run(Path(args.baseline_run).resolve())
    if baseline is None:
        raise FileNotFoundError(f"Baseline run not found: {args.baseline_run}")

    seen: set[Path] = set()
    candidates: list[RunArtifacts] = []
    for candidate in args.candidate_run:
        path = Path(candidate).resolve()
        if path in seen:
            continue
        seen.add(path)
        run = load_run(path)
        if run is not None:
            candidates.append(run)

    report = render_report(baseline, candidates)
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote comparison report to {output_path}")


if __name__ == "__main__":
    main()
