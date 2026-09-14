"""Prospective analysis of precomputed verification-policy execution records.

No model or program is executed. All twenty frozen policy replicates are
averaged within source task before uncertainty is estimated across tasks.
Missing observations remain operational misses and are also reported separately.
Only explicitly eligible rows enter contrasts. This is a finite public-test-pool
policy characterization, not a model persuasion or broad testing SOTA result.
"""
import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from analysis import canonical, derived_seed, load_jsonl_bytes, rate, _quantile

POLICIES = ("fixed", "uniform", "edit", "complement", "hybrid")
SEED = "praxis008-offline-analysis-v1"
EXPECTED_REPLICATES = tuple(range(20))
KEY = ("task_id", "split", "cohort", "proposer", "intent", "proposal_id", "replicate", "budget")


def _normalize(row, placeholder=False):
    row = dict(row)
    required = ("task_id", "split", "cohort", "proposal_id", "direction", "policy", "replicate", "budget", "eligible")
    if any(name not in row for name in required):
        raise ValueError("Missing required offline assignment field")
    if not isinstance(row["task_id"], (str, int)) or isinstance(row["task_id"], bool):
        raise ValueError("Invalid offline task ID")
    row["task_id"] = str(row["task_id"])
    if row["split"] not in ("dev", "heldout") or row["cohort"] not in ("native", "generated"):
        raise ValueError("Invalid offline cohort/split")
    if row["direction"] not in ("harmful", "useful", "other", "unknown"):
        raise ValueError("Invalid reserved-outcome direction")
    if row["policy"] not in POLICIES:
        raise ValueError("Use canonical policy names fixed/uniform/edit/complement/hybrid")
    if not isinstance(row["proposal_id"], str) or not row["proposal_id"]:
        raise ValueError("A stable proposal_id is required")
    if type(row["replicate"]) is not int or row["replicate"] < 0 or type(row["budget"]) is not int or row["budget"] < 0:
        raise ValueError("Offline replicate/budget must be nonnegative integers")
    if type(row["eligible"]) is not bool:
        raise ValueError("Offline eligibility must be explicitly boolean")
    row.setdefault("proposer", None)
    row.setdefault("intent", None)
    row.setdefault("eligibility_reasons", [])
    row.setdefault("supplier_feasible", None)
    if row["supplier_feasible"] is not None and type(row["supplier_feasible"]) is not bool:
        raise ValueError("supplier_feasible must be bool or null")
    if any(row[name] is not None and not isinstance(row[name], str) for name in ("proposer", "intent")):
        raise ValueError("Invalid proposer/intent")
    if not isinstance(row["eligibility_reasons"], list) or any(not isinstance(x, str) for x in row["eligibility_reasons"]):
        raise ValueError("eligibility_reasons must be a list of strings")
    if placeholder:
        row.update(detected=None, logical_supplier_executions=None, logical_independent_executions=None, _missing_row=True)
    for name in ("detected", "logical_supplier_executions", "logical_independent_executions"):
        if name not in row:
            raise ValueError("Missing offline observation field: " + name)
    if row["detected"] is not None and type(row["detected"]) is not bool:
        raise ValueError("detected must be bool or null")
    for name in ("logical_supplier_executions", "logical_independent_executions"):
        if row[name] is not None and (type(row[name]) is not int or row[name] < 0):
            raise ValueError("Logical execution costs must be nonnegative integers or null")
    row.setdefault("_missing_row", False)
    return row


def _key(row):
    return tuple(row[name] for name in KEY)


def prepare_rows(rows, expected_assignments=None):
    observed = {}
    for source in rows:
        row = _normalize(source)
        key = _key(row) + (row["policy"],)
        if key in observed:
            raise ValueError("Duplicate offline assignment")
        observed[key] = row
    mode = "runner_rows_only_absent_assignments_not_inferable"
    if expected_assignments is not None:
        mode = "explicit_expected_assignment_inventory"
        expected = {}
        for source in expected_assignments:
            row = _normalize(source, placeholder=True)
            key = _key(row) + (row["policy"],)
            if key in expected:
                raise ValueError("Duplicate expected offline assignment")
            expected[key] = row
        if set(observed) - set(expected):
            raise ValueError("Offline rows outside expected assignment inventory")
        for key, row in observed.items():
            if any(row[name] != expected[key][name] for name in ("direction", "eligible", "eligibility_reasons")):
                raise ValueError("Offline observation contradicts frozen assignment")
            expected[key] = row
        observed = expected
    result = sorted(observed.values(), key=lambda row: canonical(_key(row) + (row["policy"],)))
    splits, labels = {}, {}
    for row in result:
        task = row["task_id"]
        if task in splits and splits[task] != row["split"]:
            raise ValueError("Offline source task crosses data splits")
        splits[task] = row["split"]
        key = (task, row["cohort"], row["proposer"], row["proposal_id"])
        label = (row["direction"], row["eligible"], tuple(sorted(row["eligibility_reasons"])), row["intent"])
        if key in labels and labels[key] != label:
            raise ValueError("Offline direction/eligibility/intent differs across policies or replicates")
        labels[key] = label
    return result, mode


def summarize(rows):
    detected = sum(row["detected"] is True for row in rows)
    known = sum(row["detected"] is not None for row in rows)
    return {
        "assigned_rows": len(rows), "independent_tasks": len({row["task_id"] for row in rows}),
        "missing_rows": sum(row["_missing_row"] for row in rows),
        "unknown_detection_rows": len(rows) - known,
        "operational_detection_all_assigned": rate(detected, len(rows)),
        "operational_miss_all_assigned": rate(len(rows) - detected, len(rows)),
        "detection_known_only": rate(detected, known),
        "supplier_feasibility": {"fully_feasible": sum(row["supplier_feasible"] is True for row in rows),
                                 "infeasible": sum(row["supplier_feasible"] is False for row in rows),
                                 "unknown": sum(row["supplier_feasible"] is None for row in rows)},
        "detection_supplier_fully_feasible_only": rate(sum(row["detected"] is True for row in rows if row["supplier_feasible"] is True),
                                                       sum(row["supplier_feasible"] is True for row in rows)),
        "eligibility_reasons": dict(sorted(Counter(reason for row in rows for reason in row["eligibility_reasons"]).items())),
        "logical_costs": {name: {"total_known": sum(row[name] for row in rows if row[name] is not None),
                                  "unknown_rows": sum(row[name] is None for row in rows)}
                          for name in ("logical_supplier_executions", "logical_independent_executions")},
    }


def compare(rows, left, right="hybrid", expected_replicates=EXPECTED_REPLICATES,
            bootstrap_samples=5000, seed=SEED):
    """Compare left-minus-right operational misses; positive favors right.

    This function expects a single split/cohort/intent/direction/budget stratum.
    Each task receives equal weight after averaging its paired repetitions and
    proposals. Exact sign tests on twenty repetitions would be invalid and are
    deliberately absent. Complete task means are bootstrapped, never rows.
    """
    if left not in POLICIES or right not in POLICIES or left == right:
        raise ValueError("Invalid policy comparison")
    if type(bootstrap_samples) is not int or bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    expected_replicates = tuple(expected_replicates)
    if not expected_replicates or len(set(expected_replicates)) != len(expected_replicates) or any(type(x) is not int or x < 0 for x in expected_replicates):
        raise ValueError("Invalid frozen replicate set")
    strata = {(row["split"], row["cohort"], row["proposer"], row["intent"], row["direction"], row["budget"]) for row in rows}
    if len(strata) > 1:
        raise ValueError("Offline comparisons must not pool splits, intents, directions, or budgets")
    by_policy = {policy: {} for policy in (left, right)}
    for row in rows:
        if row["policy"] in by_policy:
            key = _key(row)
            if key in by_policy[row["policy"]]:
                raise ValueError("Duplicate offline pair unit")
            by_policy[row["policy"]][key] = row
    left_keys, right_keys = set(by_policy[left]), set(by_policy[right])
    common = left_keys & right_keys
    proposals = defaultdict(set)
    task_differences = defaultdict(list)
    known_task_differences = defaultdict(list)
    missing_detection_pairs = cost_mismatch_pairs = cost_unknown_pairs = 0
    budget_violations = {policy: {"supplier_over_16_rows": 0, "independent_over_requested_rows": 0}
                         for policy in (left, right)}
    for policy in (left, right):
        for row in by_policy[policy].values():
            if row["logical_supplier_executions"] is not None and row["logical_supplier_executions"] > 16:
                budget_violations[policy]["supplier_over_16_rows"] += 1
            if row["logical_independent_executions"] is not None and row["logical_independent_executions"] > row["budget"]:
                budget_violations[policy]["independent_over_requested_rows"] += 1
    for key in sorted(common, key=canonical):
        a, b = by_policy[left][key], by_policy[right][key]
        proposals[(a["task_id"], a["proposal_id"])].add(a["replicate"])
        task_differences[a["task_id"]].append(int(b["detected"] is True) - int(a["detected"] is True))
        if a["detected"] is None or b["detected"] is None:
            missing_detection_pairs += 1
        else:
            known_task_differences[a["task_id"]].append(int(b["detected"]) - int(a["detected"]))
        cost_fields = ("logical_supplier_executions", "logical_independent_executions")
        if any(a[name] is None or b[name] is None for name in cost_fields):
            cost_unknown_pairs += 1
        elif any(a[name] != b[name] for name in cost_fields):
            cost_mismatch_pairs += 1
    task_means = [sum(values) / len(values) for _, values in sorted(task_differences.items())]
    known_means = [sum(values) / len(values) for _, values in sorted(known_task_differences.items())]
    rng = random.Random(derived_seed(seed, left, right))
    estimates = [sum(task_means[rng.randrange(len(task_means))] for _ in task_means) / len(task_means)
                 for _ in range(bootstrap_samples)] if task_means else []
    missing_replicates = sum(len(set(expected_replicates) - actual) for actual in proposals.values())
    extra_replicates = sum(len(actual - set(expected_replicates)) for actual in proposals.values())
    # Completely unpaired proposals must also appear in completeness diagnostics.
    all_proposals = {(by_policy[policy][key]["task_id"], by_policy[policy][key]["proposal_id"])
                     for policy in (left, right) for key in by_policy[policy]}
    entirely_unpaired = len(all_proposals - set(proposals))
    complete = bool(task_means) and not (left_keys - right_keys or right_keys - left_keys or missing_replicates or extra_replicates or entirely_unpaired)
    difference = sum(task_means) / len(task_means) if task_means else None
    ci = [_quantile(estimates, 0.025), _quantile(estimates, 0.975)] if estimates else None
    return {
        "left": left, "right": right, "estimand": "left_minus_right_operational_miss; equally weighted task means over paired replicates",
        "difference": difference, "ci95": ci,
        "known_detection_only_difference": sum(known_means) / len(known_means) if known_means else None,
        "known_detection_only_task_count": len(known_means),
        "paired_rows": len(common), "independent_tasks": len(task_means),
        "left_assigned": len(left_keys), "right_assigned": len(right_keys),
        "left_only_unpaired": len(left_keys - right_keys), "right_only_unpaired": len(right_keys - left_keys),
        "expected_replicates": list(expected_replicates), "missing_paired_replicates": missing_replicates,
        "extra_paired_replicates": extra_replicates, "entirely_unpaired_proposals": entirely_unpaired,
        "missing_detection_pairs": missing_detection_pairs,
        "logical_cost_mismatch_pairs": cost_mismatch_pairs, "logical_cost_unknown_pairs": cost_unknown_pairs,
        "complete_arm_and_replicate_pairing": complete,
        "matched_logical_costs": bool(common) and cost_mismatch_pairs == 0 and cost_unknown_pairs == 0,
        "requested_budget_violations": budget_violations,
        "within_frozen_requested_budgets": not any(count for costs in budget_violations.values() for count in costs.values()),
        "minimum_40_tasks": len(task_means) >= 40,
        "all_zero_task_differences": bool(task_means) and all(value == 0 for value in task_means),
        "bootstrap_degenerate": bool(task_means) and len(set(task_means)) == 1,
        "bootstrap_samples": bootstrap_samples, "bootstrap_seed": str(seed),
        "ci_method": "95% percentile bootstrap of source-task means; repetitions are never independent units",
        "harm_margin_005_and_ci_excludes_zero": difference is not None and difference >= 0.05 and ci[0] > 0,
    }


def analyze(rows, expected_assignments=None, expected_replicates=EXPECTED_REPLICATES,
            bootstrap_samples=5000, seed=SEED):
    rows, mode = prepare_rows(rows, expected_assignments)
    grouping = ("split", "cohort", "proposer", "intent", "direction", "budget", "policy", "eligible")
    groups = defaultdict(list)
    strata = defaultdict(list)
    for row in rows:
        groups[tuple(row[name] for name in grouping)].append(row)
        if row["eligible"]:
            strata[tuple(row[name] for name in grouping[:6])].append(row)
    counts = [{"group": dict(zip(grouping, key)), **summarize(value)}
              for key, value in sorted(groups.items(), key=lambda item: canonical(item[0]))]
    comparisons, gates = [], []
    for key, subset in sorted(strata.items(), key=lambda item: canonical(item[0])):
        local = {}
        for left in ("uniform", "edit", "fixed", "complement"):
            result = compare(subset, left, "hybrid", expected_replicates, bootstrap_samples,
                             canonical((seed, key)))
            result["group"] = dict(zip(grouping[:6], key))
            result["role"] = "primary_offline_characterization" if key[0] == "heldout" and key[1] == "native" and key[4] == "harmful" and key[5] == 8 else "secondary_descriptive"
            comparisons.append(result)
            local[left] = result
        uniform, edit = local["uniform"], local["edit"]
        adequate = uniform["minimum_40_tasks"] and edit["minimum_40_tasks"]
        complete = uniform["complete_arm_and_replicate_pairing"] and edit["complete_arm_and_replicate_pairing"]
        observed = uniform["missing_detection_pairs"] == 0 and edit["missing_detection_pairs"] == 0
        matched = uniform["matched_logical_costs"] and edit["matched_logical_costs"]
        within_budget = uniform["within_frozen_requested_budgets"] and edit["within_frozen_requested_budgets"]
        edit_direction = edit["difference"] is not None and edit["difference"] > 0
        primary = uniform["role"] == "primary_offline_characterization"
        gates.append({"group": dict(zip(grouping[:6], key)), "primary_stratum": primary,
                      "minimum_40_tasks": adequate, "complete_pairing_and_replicates": complete,
                      "all_detections_observed": observed, "matched_logical_costs": matched,
                      "within_frozen_requested_budgets": within_budget,
                      "uniform_harm_margin_and_ci": uniform["harm_margin_005_and_ci_excludes_zero"],
                      "static_edit_directional_benefit": edit_direction,
                      "static_edit_ci_excludes_zero": edit["ci95"] is not None and edit["ci95"][0] > 0,
                      "bounded_offline_criteria_met": primary and adequate and complete and observed and matched and within_budget
                          and uniform["harm_margin_005_and_ci_excludes_zero"] and edit_direction,
                      "interpretation": "Offline finite-pool characterization only. Model usefulness/acceptance, population generalization, and superiority to coverage/differential testing remain separate."})
    return {
        "schema_version": "praxis008-offline-analysis-v1",
        "configuration": {"expected_replicates": list(expected_replicates), "bootstrap_samples": bootstrap_samples,
                          "seed": str(seed), "primary_budget": 8, "secondary_budget": 4,
                          "recommendation_minimum_tasks": 40},
        "accounting": {"assignment_mode": mode, "assigned_rows": len(rows),
                       "independent_tasks": len({row["task_id"] for row in rows}),
                       "eligible_rows": sum(row["eligible"] for row in rows),
                       "ineligible_rows": sum(not row["eligible"] for row in rows),
                       "missing_rows_materialized": sum(row["_missing_row"] for row in rows),
                       "unknown_detection_rows": sum(row["detected"] is None for row in rows)},
        "interpretation": [
            "Reserved outcome direction is supplied by the frozen analyst oracle; selectors do not receive it.",
            "Unknown detection is an operational miss, never evidence that execution observed no failure; known-only rates are separately reported.",
            "All frozen replicates are averaged within source task. More seeds/proposals are not more independent tasks.",
            "Logical acquisition counts are per-condition experimental budgets, not measured cloud billing or necessarily physically repeated executions.",
            "Useful-direction detected failures indicate disagreement between displayed verification tests and reserved-suite passing; they are not automatically verified semantic false positives.",
            "A degenerate empirical bootstrap interval does not establish a population guarantee.",
            "Absent entire tasks cannot be recovered without expected assignments or complete runner placeholders.",
        ],
        "policy_counts": counts, "comparisons": comparisons, "recommendation_gates": gates,
    }


def render_markdown(report):
    def fmt(value):
        return "undefined" if value is None else f"{value:.4f}"

    lines = ["# Offline policy characterization", "", f"Assigned rows: {report['accounting']['assigned_rows']}; independent source tasks: {report['accounting']['independent_tasks']}.",
             "", "Positive differences favor hybrid. Twenty policy replicates are averaged within each task before task-level bootstrap resampling.", "",
             "| Split/cohort/direction | Intent | Budget | Contrast | Tasks | Paired rows | Miss reduction | CI95 | Complete | Matched cost |",
             "|---|---|---:|---|---:|---:|---:|---|---|---|"]
    for row in report["comparisons"]:
        group = row["group"]
        ci = "undefined" if row["ci95"] is None else "[" + ", ".join(fmt(x) for x in row["ci95"]) + "]"
        lines.append(f"| {group['split']}/{group['cohort']}/{group['direction']} | {group['intent']} | {group['budget']} | {row['left']} - {row['right']} | {row['independent_tasks']} | {row['paired_rows']} | {fmt(row['difference'])} | {ci} | {row['complete_arm_and_replicate_pairing']} | {row['matched_logical_costs']} |")
    lines.extend(["", "Only eligible heldout native harmful revisions at budget8 are primary offline characterization. Budget4 and generated intent cohorts remain secondary. Counts and costs for every assignment, including exclusions and missing records, are in the accompanying JSON.", ""])
    lines.extend("- " + item for item in report["interpretation"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records")
    parser.add_argument("--expected-assignments")
    parser.add_argument("--frozen-protocol", required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    args = parser.parse_args()
    protocol_hash = hashlib.sha256(Path(args.frozen_protocol).read_bytes()).hexdigest()
    if protocol_hash != args.expected_protocol_sha256.lower():
        raise ValueError("Frozen protocol hash mismatch; do not inspect policy outcomes")
    record_bytes = Path(args.records).read_bytes()
    expected_bytes = Path(args.expected_assignments).read_bytes() if args.expected_assignments else None
    expected = load_jsonl_bytes(expected_bytes, args.expected_assignments) if expected_bytes is not None else None
    report = analyze(load_jsonl_bytes(record_bytes, args.records), expected)
    report["provenance"] = {"frozen_protocol_sha256": protocol_hash,
                            "records_sha256": hashlib.sha256(record_bytes).hexdigest(),
                            "expected_assignments_sha256": hashlib.sha256(expected_bytes).hexdigest() if expected_bytes is not None else None,
                            "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            "shared_analysis_source_sha256": hashlib.sha256(Path(__file__).with_name("analysis.py").read_bytes()).hexdigest()}
    Path(args.output_json).write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    Path(args.output_markdown).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
