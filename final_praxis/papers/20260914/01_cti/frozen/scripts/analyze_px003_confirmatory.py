from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_TREATMENT = "relationship_evidence"
DEFAULT_CONTROLS = (
    "vanilla",
    "technique_only_evidence",
    "random_facts",
    "empty_evidence",
    "broad_seed",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def correctness(row: dict[str, Any]) -> bool:
    if "correct" in row:
        return bool(row["correct"])
    return str(row.get("parsed_answer", "")).strip().upper() == str(
        row.get("expected_output", "")
    ).strip().upper()


def valid_answer(row: dict[str, Any]) -> bool:
    answer = str(row.get("parsed_answer", "")).strip().upper()
    expected = str(row.get("expected_output", "")).strip().upper()
    alphabet = {"A", "B", "C", "D", "E"} if expected == "E" else {"A", "B", "C", "D"}
    return answer in alphabet


def index_predictions(
    rows: Iterable[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    indexed: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        row_id = str(row.get("id", ""))
        condition = str(row.get("condition", ""))
        if not row_id or not condition:
            raise ValueError("Every prediction needs non-empty id and condition fields")
        if condition in indexed[row_id]:
            raise ValueError(f"Duplicate prediction for id={row_id!r}, condition={condition!r}")
        indexed[row_id][condition] = row
    return dict(indexed)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return (math.nan, math.nan)
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    radius = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return (max(0.0, center - radius), min(1.0, center + radius))


def quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return math.nan
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def bootstrap_paired_difference(
    differences: list[int],
    replicates: int,
    seed: int,
) -> tuple[float, float]:
    if not differences:
        return (math.nan, math.nan)
    rng = random.Random(seed)
    total = len(differences)
    samples = []
    for _ in range(replicates):
        samples.append(sum(differences[rng.randrange(total)] for _ in range(total)) / total)
    samples.sort()
    return (quantile(samples, 0.025), quantile(samples, 0.975))


def exact_mcnemar_pvalue(treatment_only: int, control_only: int) -> float:
    discordant = treatment_only + control_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(treatment_only, control_only) + 1))
    # Keep the denominator as an integer. Converting 2**n to float overflows
    # for the full 2,500-row experiment, while Python's integer true division
    # performs a correctly scaled conversion.
    return min(1.0, (2 * tail) / (1 << discordant))


def deterministic_seed(*parts: str) -> int:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def summarize_condition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    correct = sum(correctness(row) for row in rows)
    valid = sum(valid_answer(row) for row in rows)
    lower, upper = wilson_interval(correct, total)
    return {
        "rows": total,
        "correct": correct,
        "accuracy": correct / total if total else math.nan,
        "accuracy_ci95": [lower, upper],
        "invalid": total - valid,
        "invalid_rate": (total - valid) / total if total else math.nan,
    }


def compare_conditions(
    indexed: dict[str, dict[str, dict[str, Any]]],
    treatment: str,
    control: str,
    bootstrap_replicates: int,
    seed_namespace: str,
) -> dict[str, Any]:
    paired_ids = sorted(
        row_id
        for row_id, row in indexed.items()
        if treatment in row and control in row
    )
    if not paired_ids:
        raise ValueError(f"No paired rows for {treatment!r} versus {control!r}")
    differences: list[int] = []
    cells: Counter[str] = Counter()
    for row_id in paired_ids:
        treatment_correct = correctness(indexed[row_id][treatment])
        control_correct = correctness(indexed[row_id][control])
        differences.append(int(treatment_correct) - int(control_correct))
        if treatment_correct and control_correct:
            cells["both_correct"] += 1
        elif treatment_correct:
            cells["treatment_only"] += 1
        elif control_correct:
            cells["control_only"] += 1
        else:
            cells["both_wrong"] += 1
    delta = sum(differences) / len(differences)
    ci_lower, ci_upper = bootstrap_paired_difference(
        differences,
        replicates=bootstrap_replicates,
        seed=deterministic_seed(seed_namespace, treatment, control),
    )
    return {
        "treatment": treatment,
        "control": control,
        "paired_rows": len(paired_ids),
        "accuracy_difference": delta,
        "paired_bootstrap_ci95": [ci_lower, ci_upper],
        "both_correct": cells["both_correct"],
        "treatment_only": cells["treatment_only"],
        "control_only": cells["control_only"],
        "both_wrong": cells["both_wrong"],
        "discordant_rows": cells["treatment_only"] + cells["control_only"],
        "mcnemar_exact_p": exact_mcnemar_pvalue(
            cells["treatment_only"], cells["control_only"]
        ),
    }


def holm_adjust(comparisons: list[dict[str, Any]]) -> None:
    ordered = sorted(
        enumerate(comparisons), key=lambda pair: pair[1]["mcnemar_exact_p"]
    )
    running_max = 0.0
    total = len(ordered)
    for rank, (original_index, comparison) in enumerate(ordered):
        adjusted = min(1.0, comparison["mcnemar_exact_p"] * (total - rank))
        running_max = max(running_max, adjusted)
        comparisons[original_index]["mcnemar_holm_p"] = running_max


def evaluate_preregistered_gate(comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    by_control = {row["control"]: row for row in comparisons}
    required = [control for control in DEFAULT_CONTROLS if control in by_control]
    vanilla = by_control.get("vanilla")
    technique = by_control.get("technique_only_evidence")
    main_effect = bool(
        vanilla
        and vanilla["accuracy_difference"] >= 0.05
        and vanilla["paired_bootstrap_ci95"][0] > 0.0
        and vanilla["mcnemar_holm_p"] < 0.05
    )
    relationship_specificity = bool(
        technique
        and technique["accuracy_difference"] >= 0.03
        and technique["paired_bootstrap_ci95"][0] > 0.0
        and technique["mcnemar_holm_p"] < 0.05
    )
    all_controls_positive = bool(
        required
        and all(
            by_control[control]["accuracy_difference"] > 0.0
            and by_control[control]["paired_bootstrap_ci95"][0] > 0.0
            for control in required
        )
    )
    if main_effect and relationship_specificity and all_controls_positive:
        status = "PASS_RELATIONSHIP_SPECIFIC_CONFIRMATION"
    elif main_effect:
        status = "PASS_RETRIEVAL_CONDITIONED_ONLY"
    else:
        status = "FAIL_CONFIRMATORY_MAIN_EFFECT"
    return {
        "status": status,
        "main_effect_vs_vanilla": main_effect,
        "relationship_specificity_vs_technique_only": relationship_specificity,
        "all_available_controls_positive_ci": all_controls_positive,
        "available_controls": required,
        "rules": {
            "main_effect": "delta >= 0.05, paired bootstrap CI lower > 0, Holm-adjusted exact McNemar p < .05",
            "relationship_specificity": "delta vs technique-only >= 0.03, paired bootstrap CI lower > 0, Holm-adjusted exact McNemar p < .05",
            "other_controls": "relationship-evidence paired-difference CI lower > 0 for every available registered control",
        },
    }


def parse_run(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--run must use MODEL=PATH")
    model, path_text = value.split("=", 1)
    if not model.strip() or not path_text.strip():
        raise argparse.ArgumentTypeError("--run must use non-empty MODEL=PATH")
    return model.strip(), Path(path_text.strip())


def analyze_run(
    model: str,
    path: Path,
    treatment: str,
    controls: tuple[str, ...],
    bootstrap_replicates: int,
) -> dict[str, Any]:
    rows = read_jsonl(path)
    indexed = index_predictions(rows)
    conditions = sorted({str(row["condition"]) for row in rows})
    summaries = {
        condition: summarize_condition(
            [row[condition] for row in indexed.values() if condition in row]
        )
        for condition in conditions
    }
    available_controls = tuple(
        control for control in controls if control in conditions and treatment in conditions
    )
    comparisons = [
        compare_conditions(
            indexed,
            treatment=treatment,
            control=control,
            bootstrap_replicates=bootstrap_replicates,
            seed_namespace=model,
        )
        for control in available_controls
    ]
    holm_adjust(comparisons)
    return {
        "model": model,
        "predictions_path": str(path),
        "predictions_sha256": sha256_file(path),
        "prediction_rows": len(rows),
        "unique_ids": len(indexed),
        "conditions": summaries,
        "comparisons": comparisons,
        "gate": evaluate_preregistered_gate(comparisons),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model",
                "treatment",
                "control",
                "paired_rows",
                "accuracy_difference",
                "ci95_lower",
                "ci95_upper",
                "treatment_only",
                "control_only",
                "mcnemar_exact_p",
                "mcnemar_holm_p",
            ],
        )
        writer.writeheader()
        for run in runs:
            for row in run["comparisons"]:
                writer.writerow(
                    {
                        "model": run["model"],
                        "treatment": row["treatment"],
                        "control": row["control"],
                        "paired_rows": row["paired_rows"],
                        "accuracy_difference": row["accuracy_difference"],
                        "ci95_lower": row["paired_bootstrap_ci95"][0],
                        "ci95_upper": row["paired_bootstrap_ci95"][1],
                        "treatment_only": row["treatment_only"],
                        "control_only": row["control_only"],
                        "mcnemar_exact_p": row["mcnemar_exact_p"],
                        "mcnemar_holm_p": row["mcnemar_holm_p"],
                    }
                )


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# PX-003/PX-034 Paired Confirmatory Analysis",
        "",
        f"Status: **{payload['portfolio_gate']}**",
        "",
        "This analysis keeps invalid outputs as failures, uses paired row-level comparisons, reports Wilson intervals for each accuracy, percentile paired-bootstrap intervals for accuracy differences, exact McNemar tests, and Holm correction within each model's registered control family.",
        "",
    ]
    for run in payload["runs"]:
        lines.extend(
            [
                f"## {run['model']}",
                "",
                f"Gate: **{run['gate']['status']}**. Predictions SHA-256: `{run['predictions_sha256']}`.",
                "",
                "| Condition | n | Accuracy | 95% Wilson CI | Invalid rate |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for condition, summary in sorted(run["conditions"].items()):
            lines.append(
                f"| `{condition}` | {summary['rows']} | {summary['accuracy']:.4f} | "
                f"[{summary['accuracy_ci95'][0]:.4f}, {summary['accuracy_ci95'][1]:.4f}] | "
                f"{summary['invalid_rate']:.4f} |"
            )
        lines.extend(
            [
                "",
                "| Treatment vs control | Paired n | Delta | Paired 95% CI | Treatment-only / control-only | Exact p | Holm p |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in run["comparisons"]:
            lines.append(
                f"| `{row['treatment']}` vs `{row['control']}` | {row['paired_rows']} | "
                f"{row['accuracy_difference']:+.4f} | "
                f"[{row['paired_bootstrap_ci95'][0]:+.4f}, {row['paired_bootstrap_ci95'][1]:+.4f}] | "
                f"{row['treatment_only']} / {row['control_only']} | "
                f"{row['mcnemar_exact_p']:.3g} | {row['mcnemar_holm_p']:.3g} |"
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", type=parse_run, required=True, metavar="MODEL=PATH")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--treatment", default=DEFAULT_TREATMENT)
    parser.add_argument("--controls", default=",".join(DEFAULT_CONTROLS))
    parser.add_argument("--bootstrap-replicates", type=int, default=20_000)
    args = parser.parse_args()
    controls = tuple(value.strip() for value in args.controls.split(",") if value.strip())
    runs = [
        analyze_run(
            model=model,
            path=path,
            treatment=args.treatment,
            controls=controls,
            bootstrap_replicates=args.bootstrap_replicates,
        )
        for model, path in args.run
    ]
    gates = [run["gate"]["status"] for run in runs]
    scope = "MULTI_MODEL" if len(runs) >= 2 else "SINGLE_MODEL"
    if runs and all(status == "PASS_RELATIONSHIP_SPECIFIC_CONFIRMATION" for status in gates):
        portfolio_gate = f"PASS_{scope}_RELATIONSHIP_SPECIFIC_CONFIRMATION"
    elif runs and all(run["gate"]["main_effect_vs_vanilla"] for run in runs):
        portfolio_gate = f"PASS_{scope}_RETRIEVAL_CONDITIONED_ONLY"
    else:
        portfolio_gate = f"FAIL_{scope}_CONFIRMATION"
    payload = {
        "analysis_version": "px003-px034-confirmatory-v1",
        "bootstrap_replicates": args.bootstrap_replicates,
        "treatment": args.treatment,
        "registered_controls": list(controls),
        "portfolio_gate": portfolio_gate,
        "runs": runs,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "paired_statistics.json", payload)
    write_csv(args.output_dir / "paired_comparisons.csv", runs)
    write_markdown(args.output_dir / "PX003_PX034_PAIRED_CONFIRMATORY_ANALYSIS.md", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
