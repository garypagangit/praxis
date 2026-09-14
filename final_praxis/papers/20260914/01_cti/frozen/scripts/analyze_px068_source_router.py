from __future__ import annotations

import argparse
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
        wilson_interval,
    )
except ModuleNotFoundError:
    from analyze_px003_confirmatory import (  # type: ignore[no-redef]
        compare_conditions,
        holm_adjust,
        index_predictions,
        read_jsonl,
        sha256_file,
        summarize_condition,
        wilson_interval,
    )


VALID_LABELS = {"A", "B", "C", "D", "E"}
BASE_CONDITIONS = {"vanilla", "relationship_evidence"}
POLICIES = ("vanilla", "relationship_evidence", "routed_policy", "oracle_policy")
PRIMARY_GATE_SCOPES = (
    "all_primary",
    "eligible",
    "ineligible",
    "non_attack",
    "other_attack_page_types",
)


def parse_model_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Prediction must use MODEL=PATH")
    model, path = value.split("=", 1)
    return model, Path(path)


def validate_freeze_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "frozen_before_target_metrics_or_model_outcomes":
        raise ValueError("PX-068 freeze manifest has the wrong status")
    for name, record in manifest.get("artifacts", {}).items():
        artifact_path = Path(record["path"])
        if not artifact_path.exists():
            raise ValueError(f"Frozen artifact is missing: {name}={artifact_path}")
        observed = sha256_file(artifact_path)
        if observed != record["sha256"]:
            raise ValueError(f"Frozen artifact hash changed: {name}")
    assertions = manifest.get("integrity_assertions", {})
    required = (
        "complete_pipeline_refit_in_each_calibration_fold",
        "five_option_label_permutation_invariance",
        "target_truth_absent_from_router_and_prompt_builder",
        "schema_inspected_row_excluded_from_primary",
        "no_target_router_label_metrics_opened",
        "no_model_outcomes_opened",
    )
    if not all(assertions.get(key) is True for key in required):
        raise ValueError("Freeze manifest is missing a required integrity assertion")
    return manifest


def unique_by_id(rows: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("id", ""))
        if not row_id or row_id in indexed:
            raise ValueError(f"{name} has missing or duplicate id={row_id!r}")
        indexed[row_id] = row
    return indexed


def router_metrics(
    truth: dict[str, dict[str, Any]], assignments: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row_id, truth_row in truth.items():
        eligible = bool(truth_row["eligible"])
        accepted = bool(assignments[row_id]["route_relationship_evidence"])
        tp += int(eligible and accepted)
        fp += int(not eligible and accepted)
        tn += int(not eligible and not accepted)
        fn += int(eligible and not accepted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    coverage = (tp + fp) / len(truth)
    return {
        "rows": len(truth),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "precision_ci95": list(wilson_interval(tp, tp + fp)),
        "recall": recall,
        "recall_ci95": list(wilson_interval(tp, tp + fn)),
        "false_positive_rate": fpr,
        "false_positive_rate_ci95": list(wilson_interval(fp, fp + tn)),
        "specificity": specificity,
        "specificity_ci95": list(wilson_interval(tn, tn + fp)),
        "balanced_accuracy": (recall + specificity) / 2.0,
        "treatment_coverage": coverage,
    }


def base_prediction_index(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    rows = read_jsonl(path)
    indexed = index_predictions(rows)
    for row_id, by_condition in indexed.items():
        if set(by_condition) != BASE_CONDITIONS:
            raise ValueError(
                f"Prediction {row_id} has conditions {sorted(by_condition)}, expected {sorted(BASE_CONDITIONS)}"
            )
    return indexed


def policy_rows(
    truth: dict[str, dict[str, Any]],
    assignments: dict[str, dict[str, Any]],
    predictions: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    if set(truth) != set(assignments) or set(truth) != set(predictions):
        raise ValueError("Truth, assignments, and prediction ID sets differ")
    rows: list[dict[str, Any]] = []
    for row_id in sorted(truth):
        truth_row = truth[row_id]
        expected = str(truth_row["answer"]).upper()
        if expected not in VALID_LABELS:
            raise ValueError(f"Invalid truth label for {row_id}")
        vanilla = predictions[row_id]["vanilla"]
        relationship = predictions[row_id]["relationship_evidence"]
        accepted = bool(assignments[row_id]["route_relationship_evidence"])
        eligible = bool(truth_row["eligible"])
        selected = {
            "vanilla": vanilla,
            "relationship_evidence": relationship,
            "routed_policy": relationship if accepted else vanilla,
            "oracle_policy": relationship if eligible else vanilla,
        }
        for policy, prediction in selected.items():
            parsed = str(prediction.get("parsed_answer", "")).upper()
            rows.append(
                {
                    "id": row_id,
                    "condition": policy,
                    "parsed_answer": parsed,
                    "expected_output": expected,
                    "correct": parsed == expected,
                    "valid": parsed in VALID_LABELS,
                    "eligible": eligible,
                    "source_type": str(truth_row.get("source_type", "")),
                    "attack_path_type": str(truth_row.get("attack_path_type", "")),
                }
            )
    return rows


def scope_rows(rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    if scope == "all_primary":
        return rows
    if scope == "eligible":
        return [row for row in rows if row["eligible"]]
    if scope == "ineligible":
        return [row for row in rows if not row["eligible"]]
    if scope == "non_attack":
        return [row for row in rows if row["source_type"] != "mitre_attack"]
    if scope == "other_attack_page_types":
        return [
            row
            for row in rows
            if row["source_type"] == "mitre_attack" and not row["eligible"]
        ]
    if scope.startswith("source_type="):
        source_type = scope.split("=", 1)[1]
        return [row for row in rows if row["source_type"] == source_type]
    if scope.startswith("attack_path_type="):
        attack_path_type = scope.split("=", 1)[1]
        return [
            row for row in rows if row["attack_path_type"] == attack_path_type
        ]
    raise ValueError(f"Unknown scope: {scope}")


def registered_scope_names(rows: list[dict[str, Any]]) -> list[str]:
    source_types = sorted({str(row["source_type"]) for row in rows})
    attack_path_types = sorted({str(row["attack_path_type"]) for row in rows})
    return [
        *PRIMARY_GATE_SCOPES,
        *[f"source_type={value}" for value in source_types],
        *[f"attack_path_type={value}" for value in attack_path_types],
    ]


def analyze_scope(
    rows: list[dict[str, Any]],
    model: str,
    scope: str,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    scoped = scope_rows(rows, scope)
    indexed = index_predictions(scoped)
    summaries = {
        policy: summarize_condition([record[policy] for record in indexed.values()])
        for policy in POLICIES
    }
    comparisons = {
        "routed_vs_vanilla": compare_conditions(
            indexed,
            "routed_policy",
            "vanilla",
            bootstrap_replicates,
            f"px068:{model}:{scope}:routed-vs-vanilla",
        ),
        "routed_vs_ungated": compare_conditions(
            indexed,
            "routed_policy",
            "relationship_evidence",
            bootstrap_replicates,
            f"px068:{model}:{scope}:routed-vs-ungated",
        ),
        "oracle_vs_vanilla_diagnostic": compare_conditions(
            indexed,
            "oracle_policy",
            "vanilla",
            bootstrap_replicates,
            f"px068:{model}:{scope}:oracle-vs-vanilla",
        ),
    }
    return {
        "scope": scope,
        "rows": len(indexed),
        "conditions": summaries,
        "comparisons": comparisons,
    }


def add_cross_model_holm(
    analyses: dict[str, dict[str, Any]], scope: str, comparison_name: str
) -> None:
    models = sorted(analyses)
    copies = [
        dict(analyses[model]["scopes"][scope]["comparisons"][comparison_name])
        for model in models
    ]
    holm_adjust(copies)
    for model, adjusted in zip(models, copies, strict=True):
        analyses[model]["scopes"][scope]["comparisons"][comparison_name][
            "cross_model_holm_p"
        ] = adjusted["mcnemar_holm_p"]


def router_gate(metrics: dict[str, Any]) -> bool:
    return bool(
        metrics["precision"] >= 0.90
        and metrics["precision_ci95"][0] >= 0.87
        and metrics["recall"] >= 0.45
        and metrics["recall_ci95"][0] >= 0.40
        and metrics["false_positive_rate"] <= 0.05
        and metrics["false_positive_rate_ci95"][1] <= 0.07
        and 0.15 <= metrics["treatment_coverage"] <= 0.45
    )


def superiority_gate(record: dict[str, Any], minimum_delta: float) -> bool:
    return bool(
        record["accuracy_difference"] >= minimum_delta
        and record["paired_bootstrap_ci95"][0] > 0.0
        and record["cross_model_holm_p"] < 0.05
    )


def invalid_delta(scope: dict[str, Any]) -> float:
    return (
        scope["conditions"]["routed_policy"]["invalid_rate"]
        - scope["conditions"]["vanilla"]["invalid_rate"]
    )


def safety_gate(scope: dict[str, Any]) -> bool:
    comparison = scope["comparisons"]["routed_vs_vanilla"]
    return bool(
        comparison["accuracy_difference"] > -0.01
        and comparison["paired_bootstrap_ci95"][0] > -0.02
        and invalid_delta(scope) <= 0.01
    )


def evaluate_model_gates(
    record: dict[str, Any], integrity: bool, router_pass: bool
) -> dict[str, bool]:
    scopes = record["scopes"]
    return {
        "gate_0_integrity": integrity,
        "gate_1_source_compatibility": router_pass,
        "gate_2_complete_corpus_benefit": superiority_gate(
            scopes["all_primary"]["comparisons"]["routed_vs_vanilla"], 0.02
        ),
        "gate_3_eligible_benefit": superiority_gate(
            scopes["eligible"]["comparisons"]["routed_vs_vanilla"], 0.03
        ),
        "gate_4_wrong_domain_safety": bool(
            safety_gate(scopes["ineligible"])
            and safety_gate(scopes["non_attack"])
            and all(
                invalid_delta(scopes[name]) <= 0.01
                for name in PRIMARY_GATE_SCOPES
            )
        ),
        "gate_5_ungated_harm_mitigation": superiority_gate(
            scopes["ineligible"]["comparisons"]["routed_vs_ungated"], 0.05
        ),
    }


def portfolio_status(models: dict[str, Any]) -> str:
    if models and all(all(record["gates"].values()) for record in models.values()):
        return "PASS_ROUTED_EXTERNAL_CONFIRMATION"
    safety_keys = (
        "gate_0_integrity",
        "gate_1_source_compatibility",
        "gate_4_wrong_domain_safety",
        "gate_5_ungated_harm_mitigation",
    )
    if models and all(
        all(record["gates"][key] for key in safety_keys) for record in models.values()
    ):
        return "PASS_ROUTER_SAFETY_ONLY"
    return "FAIL_ROUTER_CONFIRMATION"


def schema_sensitivity_appendix(
    manifest: dict[str, Any],
    truth_path: Path,
    assignment_path: Path,
    prediction_pairs: list[tuple[str, Path]],
    primary_models: set[str],
    bootstrap_replicates: int,
) -> dict[str, Any]:
    truth = unique_by_id(read_jsonl(truth_path), "schema-sensitivity truth")
    assignments = unique_by_id(
        read_jsonl(assignment_path), "schema-sensitivity assignments"
    )
    if len(truth) != manifest["schema_sensitivity_question_rows"]:
        raise ValueError("Schema-sensitivity truth row count differs from freeze")
    prediction_paths = dict(prediction_pairs)
    if set(prediction_paths) != primary_models:
        raise ValueError(
            "Schema-sensitivity and primary prediction model names must match"
        )
    models: dict[str, Any] = {}
    for model, path in sorted(prediction_paths.items()):
        policies = policy_rows(truth, assignments, base_prediction_index(path))
        models[model] = {
            "prediction_path": str(path),
            "prediction_sha256": sha256_file(path),
            "all_three_rows_descriptive": analyze_scope(
                policies,
                model,
                "all_primary",
                bootstrap_replicates,
            ),
        }
    return {
        "role": "prospectively_excluded_three_row_descriptive_appendix_no_gate",
        "rows": len(truth),
        "router_metrics_descriptive": router_metrics(truth, assignments),
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--sealed-truth", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--prediction", action="append", type=parse_model_path, required=True)
    parser.add_argument("--sensitivity-truth", type=Path)
    parser.add_argument("--sensitivity-assignments", type=Path)
    parser.add_argument(
        "--sensitivity-prediction", action="append", type=parse_model_path
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=20_000)
    args = parser.parse_args()

    manifest = validate_freeze_manifest(args.freeze_manifest)
    truth = unique_by_id(read_jsonl(args.sealed_truth), "sealed truth")
    assignments = unique_by_id(read_jsonl(args.assignments), "assignments")
    if len(truth) != manifest["primary_question_rows"]:
        raise ValueError("Primary truth row count differs from frozen manifest")
    metrics = router_metrics(truth, assignments)
    router_pass = router_gate(metrics)
    prediction_paths = dict(args.prediction)
    if len(prediction_paths) != 2:
        raise ValueError("Exactly two model prediction files are required")

    models: dict[str, Any] = {}
    for model, path in sorted(prediction_paths.items()):
        policies = policy_rows(truth, assignments, base_prediction_index(path))
        scope_names = registered_scope_names(policies)
        models[model] = {
            "prediction_path": str(path),
            "prediction_sha256": sha256_file(path),
            "oracle_policy_is_diagnostic_only": True,
            "primary_gate_scopes": list(PRIMARY_GATE_SCOPES),
            "source_and_attack_path_subgroups_are_descriptive": True,
            "scopes": {
                scope: analyze_scope(
                    policies, model, scope, args.bootstrap_replicates
                )
                for scope in scope_names
            },
        }

    for scope, contrast in (
        ("all_primary", "routed_vs_vanilla"),
        ("eligible", "routed_vs_vanilla"),
        ("ineligible", "routed_vs_ungated"),
    ):
        add_cross_model_holm(models, scope, contrast)
    for record in models.values():
        record["gates"] = evaluate_model_gates(record, True, router_pass)

    payload = {
        "analysis_version": "px068-source-compatibility-router-v1",
        "bootstrap_replicates": args.bootstrap_replicates,
        "portfolio_status": portfolio_status(models),
        "router_metrics": metrics,
        "router_gate_pass": router_pass,
        "oracle_policy_role": "diagnostic_upper_bound_only_not_a_confirmatory_gate",
        "models": models,
    }
    sensitivity_args = (
        args.sensitivity_truth,
        args.sensitivity_assignments,
        args.sensitivity_prediction,
    )
    if any(value is not None for value in sensitivity_args):
        if not all(value is not None for value in sensitivity_args):
            raise ValueError(
                "Schema sensitivity requires truth, assignments, and predictions"
            )
        payload["schema_sensitivity"] = schema_sensitivity_appendix(
            manifest,
            args.sensitivity_truth,
            args.sensitivity_assignments,
            args.sensitivity_prediction,
            set(prediction_paths),
            args.bootstrap_replicates,
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "analysis.json"
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "portfolio_status": payload["portfolio_status"],
                "analysis_sha256": sha256_file(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
