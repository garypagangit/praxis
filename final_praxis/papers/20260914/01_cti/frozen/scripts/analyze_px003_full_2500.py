from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

try:
    from scripts.analyze_px003_confirmatory import (
        compare_conditions,
        holm_adjust,
        index_predictions,
        read_jsonl,
        sha256_file,
        summarize_condition,
    )
except ModuleNotFoundError:  # Direct execution adds scripts/, not the repository root.
    from analyze_px003_confirmatory import (  # type: ignore[no-redef]
        compare_conditions,
        holm_adjust,
        index_predictions,
        read_jsonl,
        sha256_file,
        summarize_condition,
    )


TREATMENT = "relationship_evidence"
SOURCE_CONTROLS = (
    "vanilla",
    "technique_only_evidence",
    "random_facts",
    "empty_evidence",
    "broad_seed",
)
QUERY_CONTROLS = ("vanilla",)
ATTACK_STRATUM = "attack_technique_eligible"
MISMATCH_STRATUM = "non_attack_domain_mismatch"


def parse_run(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Run must use MODEL=PATH")
    model, path = value.split("=", 1)
    if not model or not path:
        raise argparse.ArgumentTypeError("Run must use non-empty MODEL=PATH")
    return model, Path(path)


def validate_strata(rows: list[dict[str, Any]]) -> None:
    strata_by_id: dict[str, str] = {}
    for row in rows:
        row_id = str(row.get("id", ""))
        stratum = str(row.get("dataset_stratum", ""))
        if stratum not in {ATTACK_STRATUM, MISMATCH_STRATUM}:
            raise ValueError(f"Missing or unknown dataset_stratum for {row_id}: {stratum!r}")
        previous = strata_by_id.setdefault(row_id, stratum)
        if previous != stratum:
            raise ValueError(f"Inconsistent dataset_stratum for {row_id}")


def analyze_rows(
    rows: list[dict[str, Any]],
    model: str,
    cell: str,
    scope: str,
    controls: tuple[str, ...],
    bootstrap_replicates: int,
) -> dict[str, Any]:
    indexed = index_predictions(rows)
    conditions = sorted({str(row["condition"]) for row in rows})
    expected_conditions = {TREATMENT, *controls}
    if set(conditions) != expected_conditions:
        raise ValueError(
            f"{model}/{cell}/{scope}: conditions {conditions} do not match "
            f"{sorted(expected_conditions)}"
        )
    summaries = {
        condition: summarize_condition(
            [condition_rows[condition] for condition_rows in indexed.values()]
        )
        for condition in conditions
    }
    comparisons = [
        compare_conditions(
            indexed,
            treatment=TREATMENT,
            control=control,
            bootstrap_replicates=bootstrap_replicates,
            seed_namespace=f"{model}:{cell}:{scope}",
        )
        for control in controls
    ]
    holm_adjust(comparisons)
    return {
        "scope": scope,
        "unique_ids": len(indexed),
        "conditions": summaries,
        "comparisons": comparisons,
    }


def analyze_cell(
    model: str,
    path: Path,
    cell: str,
    controls: tuple[str, ...],
    bootstrap_replicates: int,
) -> dict[str, Any]:
    rows = read_jsonl(path)
    validate_strata(rows)
    strata = {
        stratum: analyze_rows(
            [row for row in rows if row["dataset_stratum"] == stratum],
            model=model,
            cell=cell,
            scope=stratum,
            controls=controls,
            bootstrap_replicates=bootstrap_replicates,
        )
        for stratum in (ATTACK_STRATUM, MISMATCH_STRATUM)
    }
    return {
        "model": model,
        "cell": cell,
        "predictions_path": str(path),
        "predictions_sha256": sha256_file(path),
        "prediction_rows": len(rows),
        "intention_to_treat": analyze_rows(
            rows,
            model=model,
            cell=cell,
            scope="all_2500",
            controls=controls,
            bootstrap_replicates=bootstrap_replicates,
        ),
        "strata": strata,
    }


def comparison(scope: dict[str, Any], control: str) -> dict[str, Any]:
    return next(row for row in scope["comparisons"] if row["control"] == control)


def invalid_safe(scope: dict[str, Any]) -> bool:
    treatment = scope["conditions"][TREATMENT]["invalid_rate"]
    vanilla = scope["conditions"]["vanilla"]["invalid_rate"]
    return bool(treatment <= vanilla + 0.03)


def evaluate_gates(source: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    source_attack = source["strata"][ATTACK_STRATUM]
    main = comparison(source_attack, "vanilla")
    technique = comparison(source_attack, "technique_only_evidence")
    negatives = [
        comparison(source_attack, control)
        for control in ("random_facts", "empty_evidence", "broad_seed")
    ]
    query_attack = query["strata"][ATTACK_STRATUM]
    query_main = comparison(query_attack, "vanilla")
    query_mismatch = comparison(query["strata"][MISMATCH_STRATUM], "vanilla")
    return {
        "source_main": bool(
            main["accuracy_difference"] >= 0.05
            and main["paired_bootstrap_ci95"][0] > 0.0
            and main["mcnemar_holm_p"] < 0.05
        ),
        "source_relationship_specificity": bool(
            technique["accuracy_difference"] >= 0.03
            and technique["paired_bootstrap_ci95"][0] > 0.0
            and technique["mcnemar_holm_p"] < 0.05
        ),
        "source_negative_controls": bool(
            all(row["paired_bootstrap_ci95"][0] > 0.0 for row in negatives)
        ),
        "query_main_pre_cross_model_holm": bool(
            query_main["accuracy_difference"] >= 0.03
            and query_main["paired_bootstrap_ci95"][0] > 0.0
        ),
        "query_mismatch_noninferiority": bool(
            query_mismatch["paired_bootstrap_ci95"][0] > -0.05
        ),
        "source_invalid_safety": invalid_safe(source_attack),
        "source_mismatch_invalid_safety": invalid_safe(
            source["strata"][MISMATCH_STRATUM]
        ),
        "query_attack_invalid_safety": invalid_safe(query_attack),
        "query_mismatch_invalid_safety": invalid_safe(query["strata"][MISMATCH_STRATUM]),
    }


def add_cross_model_query_holm(query_runs: list[dict[str, Any]]) -> None:
    comparisons = [
        comparison(run["strata"][ATTACK_STRATUM], "vanilla") for run in query_runs
    ]
    copies = [dict(row) for row in comparisons]
    holm_adjust(copies)
    for run, adjusted in zip(query_runs, copies):
        target = comparison(run["strata"][ATTACK_STRATUM], "vanilla")
        target["cross_model_holm_p"] = adjusted["mcnemar_holm_p"]


def vanilla_concordance(source_path: Path, query_path: Path) -> dict[str, Any]:
    source_rows = {
        str(row["id"]): row
        for row in read_jsonl(source_path)
        if row.get("condition") == "vanilla"
    }
    query_rows = {
        str(row["id"]): row
        for row in read_jsonl(query_path)
        if row.get("condition") == "vanilla"
    }
    if set(source_rows) != set(query_rows):
        raise ValueError("Source-pointer and query-only vanilla ID sets differ")
    answer_matches = sum(
        str(source_rows[row_id].get("parsed_answer", ""))
        == str(query_rows[row_id].get("parsed_answer", ""))
        for row_id in source_rows
    )
    correctness_matches = sum(
        bool(source_rows[row_id].get("correct"))
        == bool(query_rows[row_id].get("correct"))
        for row_id in source_rows
    )
    return {
        "rows": len(source_rows),
        "parsed_answer_matches": answer_matches,
        "parsed_answer_match_rate": answer_matches / len(source_rows),
        "correctness_matches": correctness_matches,
        "correctness_match_rate": correctness_matches / len(source_rows),
        "interpretation": "execution reproducibility diagnostic; not a treatment-effect gate",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PX-003/PX-034 all-2,500 paired analysis",
        "",
        f"Status: **{payload['portfolio_status']}**",
        "",
        "The complete 2,500-row intention-to-treat result and both preregistered strata are reported. Source-pointer claims are evaluated only on the 1,578 ATT&CK-technique-eligible rows.",
        "",
    ]
    for model in sorted(payload["models"]):
        record = payload["models"][model]
        lines.extend([f"## {model}", "", f"Gates: `{json.dumps(record['gates'], sort_keys=True)}`", ""])
        for cell_name in ("source_pointer", "query_only"):
            cell = record[cell_name]
            lines.extend([f"### {cell_name}", ""])
            for scope_name, scope in [
                ("all_2500", cell["intention_to_treat"]),
                *cell["strata"].items(),
            ]:
                lines.extend(
                    [
                        f"#### {scope_name}",
                        "",
                        "| Condition | n | Accuracy | 95% Wilson CI | Invalid rate |",
                        "|---|---:|---:|---:|---:|",
                    ]
                )
                for condition, condition_summary in sorted(scope["conditions"].items()):
                    lines.append(
                        f"| `{condition}` | {condition_summary['rows']} | "
                        f"{condition_summary['accuracy']:.4f} | "
                        f"[{condition_summary['accuracy_ci95'][0]:.4f}, "
                        f"{condition_summary['accuracy_ci95'][1]:.4f}] | "
                        f"{condition_summary['invalid_rate']:.4f} |"
                    )
                lines.extend(
                    [
                        "",
                        "| Treatment vs control | n | Delta | Paired 95% CI | Exact p | Within-cell Holm p | Cross-model Holm p |",
                        "|---|---:|---:|---:|---:|---:|---:|",
                    ]
                )
                for row in scope["comparisons"]:
                    lines.append(
                        f"| `{row['treatment']}` vs `{row['control']}` | {row['paired_rows']} | "
                        f"{row['accuracy_difference']:+.4f} | "
                        f"[{row['paired_bootstrap_ci95'][0]:+.4f}, {row['paired_bootstrap_ci95'][1]:+.4f}] | "
                        f"{row['mcnemar_exact_p']:.3g} | {row['mcnemar_holm_p']:.3g} | "
                        f"{format(row['cross_model_holm_p'], '.3g') if 'cross_model_holm_p' in row else ''} |"
                    )
                lines.append("")
    return "\n".join(lines) + "\n"


def write_comparison_csv(path: Path, models: dict[str, Any]) -> None:
    fieldnames = [
        "model",
        "cell",
        "scope",
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
        "cross_model_holm_p",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for model, record in sorted(models.items()):
            for cell_name in ("source_pointer", "query_only"):
                cell = record[cell_name]
                scopes = [
                    ("all_2500", cell["intention_to_treat"]),
                    *cell["strata"].items(),
                ]
                for scope_name, scope in scopes:
                    for row in scope["comparisons"]:
                        writer.writerow(
                            {
                                "model": model,
                                "cell": cell_name,
                                "scope": scope_name,
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
                                "cross_model_holm_p": row.get("cross_model_holm_p", ""),
                            }
                        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", action="append", type=parse_run, required=True)
    parser.add_argument("--query-run", action="append", type=parse_run, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=20_000)
    args = parser.parse_args()

    source_by_model = {
        model: analyze_cell(
            model,
            path,
            cell="source_pointer",
            controls=SOURCE_CONTROLS,
            bootstrap_replicates=args.bootstrap_replicates,
        )
        for model, path in args.source_run
    }
    query_by_model = {
        model: analyze_cell(
            model,
            path,
            cell="query_only",
            controls=QUERY_CONTROLS,
            bootstrap_replicates=args.bootstrap_replicates,
        )
        for model, path in args.query_run
    }
    if set(source_by_model) != set(query_by_model):
        raise ValueError("Source-pointer and query-only model sets must match")
    add_cross_model_query_holm(list(query_by_model.values()))

    models: dict[str, Any] = {}
    for model in sorted(source_by_model):
        gates = evaluate_gates(source_by_model[model], query_by_model[model])
        query_primary = comparison(
            query_by_model[model]["strata"][ATTACK_STRATUM], "vanilla"
        )
        gates["query_main"] = bool(
            gates["query_main_pre_cross_model_holm"]
            and query_primary["cross_model_holm_p"] < 0.05
        )
        models[model] = {
            "source_pointer": source_by_model[model],
            "query_only": query_by_model[model],
            "duplicate_vanilla_concordance": vanilla_concordance(
                Path(source_by_model[model]["predictions_path"]),
                Path(query_by_model[model]["predictions_path"]),
            ),
            "gates": gates,
        }

    all_gate_values = [record["gates"] for record in models.values()]
    full_success = bool(
        all_gate_values
        and all(
            all(
                gate[key]
                for key in (
                    "source_main",
                    "source_relationship_specificity",
                    "source_negative_controls",
                    "query_main",
                    "query_mismatch_noninferiority",
                    "source_invalid_safety",
                    "source_mismatch_invalid_safety",
                    "query_attack_invalid_safety",
                    "query_mismatch_invalid_safety",
                )
            )
            for gate in all_gate_values
        )
    )
    source_success = bool(
        all_gate_values
        and all(
            gate["source_main"]
            and gate["source_relationship_specificity"]
            and gate["source_negative_controls"]
            and gate["source_invalid_safety"]
            and gate["source_mismatch_invalid_safety"]
            for gate in all_gate_values
        )
    )
    portfolio_status = (
        "PASS_FULL_SOURCE_AND_QUERY_CONFIRMATION"
        if full_success
        else "PASS_SOURCE_KNOWN_ONLY"
        if source_success
        else "FAIL_PREREGISTERED_CONFIRMATION"
    )
    payload = {
        "analysis_version": "px003-px034-full-2500-v1",
        "bootstrap_replicates": args.bootstrap_replicates,
        "portfolio_status": portfolio_status,
        "models": models,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "analysis.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "analysis.md").write_text(render_markdown(payload), encoding="utf-8")
    write_comparison_csv(args.output_dir / "comparisons.csv", models)
    print(json.dumps({"portfolio_status": portfolio_status}, indent=2))


if __name__ == "__main__":
    main()
