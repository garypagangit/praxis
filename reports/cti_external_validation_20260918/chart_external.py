"""Draw publication figures from the complete, frozen external CTI analysis.

Default invocation, after real RESULTS.json exists:
    python reports/cti_external_validation_20260918/chart_external.py

Writes two figures, each as a 300-dpi PNG and a vector SVG, plus CHARTS.json.
Reads recorded estimates and intervals; never fits, bootstraps, or changes gates.
Incomplete attempts are rejected. This presentation artifact is outside the
scientific freeze and must not be used to replace the full comparison report.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODELS = ("llama", "qwen")
MODEL_NAMES = {"llama": "Llama 3.1 8B", "qwen": "Qwen 2.5 7B"}
CANDIDATE = "evidence_utility"
PRIMARY_ARMS = ("always_vanilla", "always_evidence", CANDIDATE)
ARM_NAMES = {
    "always_vanilla": "No retrieved evidence",
    "always_evidence": "Always use evidence",
    CANDIDATE: "Candidate checker",
}
ARM_COLORS = {"always_vanilla": "#7D8794", "always_evidence": "#C58832", CANDIDATE: "#007F83"}
MODEL_COLORS = {"llama": "#007F83", "qwen": "#6250A3"}
MODEL_MARKERS = {"llama": "o", "qwen": "s"}
COHORTS = (
    ("all", "All questions"),
    ("attack_source", "ATT&CK-source questions"),
    ("other_source", "Other-source questions"),
    ("previously_absent_broad_families", "Eight previously absent\nbroad source families"),
)
COMPLETE_STATUSES = {
    "EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE",
    "EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN",
    "EXTERNAL_TRANSPORT_CRITERIA_NOT_MET",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value, name):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), "Invalid finite number: " + name)
    return float(value)


def display_points(value):
    # Suppress signed zero after rounding; retain the recorded value for plotting.
    return "0.00" if abs(value) < 0.005 else f"{value:+.2f}"


def read_verified_results(result_path, root):
    require(result_path.is_file(), "RESULTS.json is absent; charts require a complete real analysis")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    require(result.get("status") in COMPLETE_STATUSES, "An incomplete attempt has no efficacy charts")
    require((result.get("n"), result.get("fresh_outputs"), result.get("qualification_outputs"))
            == (1247, 4988, 32), "Complete result inventory mismatch")
    expected_status = (
        ("EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE" if result["added_value"]
         else "EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN") if result["useful_signal"]
        else "EXTERNAL_TRANSPORT_CRITERIA_NOT_MET"
    )
    require(result["status"] == expected_status, "Inconsistent result decision flags")
    freeze_path = root / "SCIENTIFIC_FREEZE.json"
    require(freeze_path.is_file(), "Scientific freeze is missing")
    require(sha256(freeze_path) == result["scientific_freeze_sha256"], "Results do not match the scientific freeze")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    for name, expected_hash in freeze["files"].items():
        path = root / name
        require(path.is_file() and sha256(path) == expected_hash, "Frozen scientific file changed: " + name)
    metrics = result["metrics"]
    require(metrics["all"]["n"] == result["n"], "Overall count mismatch")
    require(metrics["attack_source"]["n"] + metrics["other_source"]["n"] == result["n"], "Primary cohort counts mismatch")
    require(0 < metrics["previously_absent_broad_families"]["n"] <= metrics["other_source"]["n"], "Invalid source subset count")
    for cohort, _ in COHORTS:
        section = metrics[cohort]
        n = section["n"]
        require(isinstance(n, int) and not isinstance(n, bool) and n > 0, "Invalid cohort count")
        for arm_name in PRIMARY_ARMS:
            arm = section["arms"][arm_name]
            use = arm["evidence_use_n"]
            require(isinstance(use, int) and 0 <= use <= n, "Invalid evidence use count")
            for model in MODELS:
                record = arm["models"][model]
                correct = record["correct"]
                accuracy = number(record["accuracy_pct"], "accuracy")
                require(isinstance(correct, int) and 0 <= correct <= n, "Invalid correct count")
                require(math.isclose(accuracy, 100 * correct / n, abs_tol=1e-8), "Accuracy disagrees with recorded counts")
        for model in MODELS:
            candidate = section["arms"][CANDIDATE]["models"][model]
            baseline = section["arms"]["always_vanilla"]["models"][model]
            delta = number(candidate["delta_vs_vanilla_pp"], "delta")
            require(math.isclose(delta, candidate["accuracy_pct"] - baseline["accuracy_pct"], abs_tol=1e-8), "Candidate delta disagrees with accuracies")
            interval = candidate["delta_ci95_pp"]
            require(isinstance(interval, list) and len(interval) == 2, "Invalid paired confidence interval")
            low, high = (number(x, "confidence interval") for x in interval)
            require(-100 <= low <= high <= 100, "Invalid confidence interval bounds")
    return result


def save_figure(fig, directory, stem, description, outputs):
    for suffix in ("png", "svg"):
        path = directory / (stem + "." + suffix)
        metadata = {"Description": description}
        fig.savefig(path, dpi=300, facecolor="white", metadata=metadata)
        outputs[path.name] = {"sha256": sha256(path), "description": description}


def plot_primary_accuracy(plt, result, directory, outputs):
    """Show absolute accuracy with an untruncated 0-100 percent scale."""
    overall = result["metrics"]["all"]
    fig, ax = plt.subplots(figsize=(9.4, 5.8))
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.23, top=0.76)
    width = 0.23
    for arm_index, arm_name in enumerate(PRIMARY_ARMS):
        values = [overall["arms"][arm_name]["models"][model]["accuracy_pct"] for model in MODELS]
        positions = [index + (arm_index - 1) * width for index in range(len(MODELS))]
        bars = ax.bar(positions, values, width=width * 0.92, color=ARM_COLORS[arm_name],
                      edgecolor="white", linewidth=0.6, label=ARM_NAMES[arm_name], zorder=3)
        for bar, value in zip(bars, values):
            ax.annotate(f"{value:.2f}%", (bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 5), textcoords="offset points", ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Accuracy against released answers (%)")
    ax.set_xticks(range(len(MODELS)), [MODEL_NAMES[model] for model in MODELS])
    ax.set_xlim(-0.6, 1.6)
    ax.grid(axis="y", color="#E1E5E9", linewidth=0.7, zorder=0)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.025), ncol=3, frameon=False, fontsize=10)
    fig.text(0.09, 0.94, "External CTI validation: primary answer policies", fontsize=16, weight="bold", ha="left")
    fig.text(0.09, 0.89, f"SecEval | {overall['n']:,} paired questions per model | frozen checker", fontsize=11, color="#455360")
    use = overall["arms"][CANDIDATE]["evidence_use_n"]
    fig.text(0.09, 0.13, f"The candidate selected evidence for {use:,}/{overall['n']:,} questions. Every policy answered every question.", fontsize=9.5)
    fig.text(0.09, 0.085, "Accuracy measures agreement with released labels; independent human review is pending.", fontsize=9.5, color="#455360")
    fig.text(0.09, 0.04, "Primary arms only. Full comparator results and prespecified decisions are in REPORT.md and RESULTS.json.", fontsize=9, color="#455360")
    save_figure(fig, directory, "primary_accuracy", "Absolute accuracy of three frozen policies on SecEval; percent scale, released labels.", outputs)
    plt.close(fig)


def plot_candidate_changes(plt, result, directory, outputs):
    """Use the existing paired CIs, including overlapping descriptive cohorts."""
    fig, ax = plt.subplots(figsize=(11.8, 6.7))
    fig.subplots_adjust(left=0.31, right=0.71, bottom=0.30, top=0.78)
    all_bounds = [0.0]
    metrics = result["metrics"]
    for cohort_index, (cohort, _) in enumerate(COHORTS):
        section = metrics[cohort]
        for model_index, model in enumerate(MODELS):
            record = section["arms"][CANDIDATE]["models"][model]
            delta, (low, high) = record["delta_vs_vanilla_pp"], record["delta_ci95_pp"]
            all_bounds.extend((delta, low, high))
            y = cohort_index + (-0.16 if model_index == 0 else 0.16)
            color = MODEL_COLORS[model]
            # Draw the interval separately: a percentile CI need not contain its estimate.
            ax.hlines(y, low, high, color=color, linewidth=1.8, zorder=3)
            ax.vlines([low, high], y - 0.045, y + 0.045, color=color, linewidth=1.4, zorder=3)
            ax.plot(delta, y, marker=MODEL_MARKERS[model], markersize=6.5, color=color,
                    linestyle="none", label=MODEL_NAMES[model] if cohort_index == 0 else None, zorder=4)
            ax.text(1.035, y, f"{display_points(delta)}  [{display_points(low)}, {display_points(high)}]",
                    transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=10, color=color)
    lower, upper = min(all_bounds), max(all_bounds)
    pad = max((upper - lower) * 0.12, 1.0)
    ax.set_xlim(lower - pad, upper + pad)
    ax.set_ylim(len(COHORTS) - 0.5, -0.55)
    ax.axvline(0, color="#64717D", linewidth=1.1, linestyle="--", zorder=2)
    ax.grid(axis="x", color="#E1E5E9", linewidth=0.7, zorder=0)
    ax.set_yticks(range(len(COHORTS)), [f"{label}\n(n = {metrics[key]['n']:,})" for key, label in COHORTS])
    ax.tick_params(axis="y", length=0, pad=12)
    ax.set_xlabel("Accuracy change from no evidence (percentage points)", labelpad=9)
    ax.text(1.035, 1.035, "Change [95% paired CI], pp", transform=ax.transAxes, ha="left", va="bottom", fontsize=10)
    fig.legend(*ax.get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(0.305, 0.857), ncol=2, frameon=False, fontsize=10)
    fig.text(0.045, 0.94, "Candidate checker: paired accuracy change", fontsize=16, weight="bold")
    fig.text(0.045, 0.89, "Each point compares candidate-selected answers with the same model's no-evidence answers.", fontsize=11, color="#455360")
    fig.text(0.045, 0.155, "Intervals: 5,000 paired bootstrap replicates, resampling questions within coarse source families.", fontsize=9.5)
    fig.text(0.045, 0.113, "The eight-family cohort is a subset of other-source questions; rows are not independent datasets.", fontsize=9.5, color="#455360")
    fig.text(0.045, 0.071, "Released labels; shared ATT&CK knowledge; source-document cluster uncertainty is not estimated.", fontsize=9.5, color="#455360")
    fig.text(0.045, 0.029, "Human review is pending. These plots do not establish algorithmic novelty or replace the full comparator analysis.", fontsize=9.5, color="#455360")
    save_figure(fig, directory, "candidate_change", "Candidate minus no-evidence accuracy in percentage points, with recorded paired 95% bootstrap intervals.", outputs)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Experiment directory containing the scientific freeze")
    parser.add_argument("--results", type=Path, help="Default: ROOT/RESULTS.json")
    parser.add_argument("--output-dir", type=Path, help="Default: ROOT")
    args = parser.parse_args()
    result_path = args.results or args.root / "RESULTS.json"
    result = read_verified_results(result_path, args.root)
    # Import plotting only after complete results and all frozen files are verified.
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.labelcolor": "#273443", "text.color": "#273443",
        "xtick.color": "#455360", "ytick.color": "#455360",
        "svg.fonttype": "none", "svg.hashsalt": "cti-external-validation-20260918",
        "savefig.transparent": False,
    })
    output_dir = args.output_dir or args.root
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    plot_primary_accuracy(plt, result, output_dir, outputs)
    plot_candidate_changes(plt, result, output_dir, outputs)
    receipt = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PRESENTATION_OF_COMPLETE_RECORDED_RESULTS",
        "results_sha256": sha256(result_path),
        "scientific_freeze_sha256": result["scientific_freeze_sha256"],
        "chart_script_sha256": sha256(Path(__file__)),
        "matplotlib_version": matplotlib.__version__,
        "recorded_analysis_status": result["status"],
        "outputs": outputs,
        "notes": ["No inference, fitting, resampling, or gate changes performed.",
                  "Accuracy is percent; paired changes and intervals are percentage points.",
                  "These figures show primary arms; use the full report for all comparators."],
    }
    (output_dir / "CHARTS.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "files": [*outputs, "CHARTS.json"]}, indent=2))


if __name__ == "__main__":
    main()
