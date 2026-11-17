"""Compile all expanded defender experiment phases into one report."""

import argparse
import json
from pathlib import Path

import defender_telemetry_experiment as base
import defender_telemetry_expanded as expanded


PHASES = ("windows", "models", "behavior", "smote")


def report(output):
    output = output.resolve()
    report_file = output / "EXPANDED_RESULTS.md"
    if report_file.exists():
        raise ValueError("Refusing to overwrite an existing report")
    manifest = json.loads((output / "extraction.json").read_text(encoding="utf-8"))
    if (manifest["script_sha256"] != base.sha256(Path(expanded.__file__).resolve())
            or manifest["original_script_sha256"] != base.sha256(Path(base.__file__).resolve())
            or manifest["windows30_sha256"] != base.sha256(output / "windows30.csv")):
        raise ValueError("Experiment code or inputs changed after extraction")
    phases = {}
    for phase in PHASES:
        data = json.loads((output / f"{phase}.json").read_text(encoding="utf-8"))
        if data["phase"] != phase or data["script_sha256"] != manifest["script_sha256"]:
            raise ValueError(f"Incorrect provenance for phase {phase}")
        phases[phase] = data
    entries = [(phase, str(size), phases[phase]["results"][str(size)])
               for phase in PHASES for size in expanded.SIZES]
    adjusted = base.holm([item["permutation_p"] if item["status"] == "complete" else 1.0
                          for _, _, item in entries])
    coverage = manifest["prior_coverage"]
    lines = [
        "# Expanded defender telemetry results",
        "",
        "**Exploratory; not independent confirmation or a benign-traffic detector.**",
        f"Nine attack sessions: {sum(x['class'] == 'human' for x in coverage.values())} human, "
        f"{sum(x['class'] == 'ai' for x in coverage.values())} AI.",
        f"30-second windows: {sum(x['candidate_windows'] for x in coverage.values())} candidates, "
        f"{sum(x['eligible_windows'] for x in coverage.values())} retained.",
        "Longer windows require every constituent 30-second window to be retained; "
        "different lengths therefore evaluate different subsets.",
        "",
        "| Phase | Seconds | Human / AI windows | Macro-F1 | 95% session interval | AI recall | Human attack FPR | Session accuracy | Raw p | Holm p (16 tests) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for (phase, size, item), p in zip(entries, adjusted):
        if item["status"] != "complete":
            lines.append(f"| {phase} | {size} | {item['windows']} total | "
                         "not evaluable: at least one session has no eligible windows |"
                         " - | - | - | - | - | - |")
            continue
        low, high = item["bootstrap_interval"]
        counts = item["windows_by_class"]
        lines.append(
            f"| {phase} | {size} | {counts['human']} / {counts['ai']} | "
            f"{item['macro_f1']:.3f} | {low:.3f}-{high:.3f} | "
            f"{item['ai_recall']:.3f} | {item['human_attack_window_fpr']:.3f} | "
            f"{item['session_accuracy']:.3f} | {item['permutation_p']:.4f} | {p:.4f} |"
        )
    lines += [
        "",
        "Phases: windows = logistic regression; models = XGBoost on baseline "
        "counts; behavior = XGBoost with additional channels and timing features; "
        "smote = the behavior model with training-fold SMOTE.",
        "Raw p-values use all 126 session-label permutations; Holm correction "
        "covers all 16 planned configurations, assigning p=1 to unavailable ones.",
        "With 126 assignments and 16 planned tests, the smallest possible "
        "first Holm-adjusted p-value is 16/126 = 0.127; this family cannot "
        "reach 0.05 with these nine sessions.",
        "Session bootstrap intervals resample fixed out-of-fold predictions, "
        "not model refits or selection.",
        "",
        "Coverage is only a coarse proxy, and the additional event channels can "
        "be sparse. Flow intervals can span windows, and flow-end assignment is "
        "not real-time latency. Some available channels were not modeled; see the "
        "runbook. Results assume exchangeable sessions, compare human versus AI "
        "attacks, and require independent validation including benign traffic.",
        "",
        "Per-session counts and predictions are in the phase JSON files. "
        "These files and extracted features are restricted.",
        "",
    ]
    report_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved {report_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    report(parser.parse_args().output)
