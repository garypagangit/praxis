"""Prospective analysis of authenticated evidence and code-revision decisions.

Only reserved-suite outcomes define harmful/useful revisions. All assigned rows
remain in accounting; missing or invalid decisions fail closed. Replicate zero is
primary. Bootstrap resampling uses source task IDs, preserving paired arms,
directions, and proposals within a sampled task. Nothing here executes models.

The CLI requires a frozen protocol and its independently supplied SHA256. The
library API is intentionally usable with synthetic controls before that freeze.
"""
import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ("no_witness", "uniform_w", "selected_w", "fixed", "edit",
        "complement", "hybrid", "uniform_a")
LAYERS = ("reviewer_only", "enforced")
DIRECTIONS = ("harmful", "useful", "other", "unknown")
DEFAULT_SEED = "praxis008-analysis-v1"
SCHEMA_VERSION = "praxis008-code-analysis-v1"
IDENTITY = ("task_id", "split", "cohort", "reviewer", "proposer",
            "proposal_id", "replicate")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def derived_seed(*parts):
    return int.from_bytes(hashlib.sha256(canonical(parts).encode()).digest()[:16], "big")


def outcome_direction(y0, y1):
    if y0 is None or y1 is None:
        return "unknown"
    if y0 and not y1:
        return "harmful"
    if not y0 and y1:
        return "useful"
    return "other"


def _normalize(row, placeholder=False):
    row = dict(row)
    for name in ("task_id", "split", "cohort", "reviewer", "arm", "replicate"):
        if name not in row:
            raise ValueError("Missing identity field: " + name)
    if not isinstance(row["task_id"], (str, int)) or isinstance(row["task_id"], bool):
        raise ValueError("task_id must be a string or integer")
    row["task_id"] = str(row["task_id"])
    if row["split"] not in ("dev", "heldout") or row["cohort"] not in ("native", "generated"):
        raise ValueError("Invalid split/cohort")
    if row["arm"] not in ARMS:
        raise ValueError("Unknown arm: " + str(row["arm"]))
    if type(row["replicate"]) is not int or row["replicate"] < 0:
        raise ValueError("replicate must be a nonnegative integer")
    if not isinstance(row["reviewer"], str) or not row["reviewer"]:
        raise ValueError("reviewer must be a nonempty frozen model ID")
    for name in ("y0", "y1"):
        if name not in row and not placeholder:
            raise ValueError("Missing reserved outcome: " + name)
        row.setdefault(name, None)
        if row[name] is not None and type(row[name]) is not bool:
            raise ValueError(name + " must be bool or null")
    direction = outcome_direction(row["y0"], row["y1"])
    supplied = row.get("direction", "other" if direction == "unknown" else direction)
    if supplied != direction and not (direction == "unknown" and supplied == "other"):
        raise ValueError("direction disagrees with reserved outcomes")
    row["direction"] = direction
    row.setdefault("proposer", None)
    row.setdefault("intent", None)
    row.setdefault("eligible", None)
    row.setdefault("eligibility_reasons", [] if row["eligible"] is not None else ["eligibility_not_declared"])
    row.setdefault("supplier_feasible", None)
    if row["supplier_feasible"] is not None and type(row["supplier_feasible"]) is not bool:
        raise ValueError("supplier_feasible must be bool or null")
    if row["eligible"] is not None and type(row["eligible"]) is not bool:
        raise ValueError("eligible must be bool or null")
    if not isinstance(row["eligibility_reasons"], list) or any(not isinstance(x, str) for x in row["eligibility_reasons"]):
        raise ValueError("eligibility_reasons must be a list of strings")
    # Explicit IDs are needed whenever several proposals share an outcome class.
    row.setdefault("proposal_id", "direction:" + direction)
    if not isinstance(row["proposal_id"], str) or not row["proposal_id"]:
        raise ValueError("proposal_id must be a nonempty string")
    for name in ("proposer", "intent"):
        if row[name] is not None and not isinstance(row[name], str):
            raise ValueError(name + " must be string or null")
    if placeholder:
        row.update(decision="abstain", authenticated_failure=False, model_valid=False,
                   proposal_status=row.get("proposal_status", "unobserved"),
                   _missing_row=True)
    for name in ("decision", "authenticated_failure", "model_valid", "proposal_status"):
        if name not in row:
            raise ValueError("Missing decision field: " + name)
    if row["decision"] not in ("accept", "keep", "abstain"):
        raise ValueError("Unparsed decisions must be encoded as abstain/model_valid=false")
    if type(row["authenticated_failure"]) is not bool or type(row["model_valid"]) is not bool:
        raise ValueError("Authentication and validity flags must be literal booleans")
    if not isinstance(row["proposal_status"], str) or not row["proposal_status"]:
        raise ValueError("proposal_status must be a nonempty string")
    row.setdefault("_missing_row", False)
    return row


def unit_key(row):
    return tuple(row[name] for name in IDENTITY)


def prepare_rows(rows, expected_assignments=None):
    """Validate identities; optionally materialize missing assigned decisions.

    An expected assignment inventory is authoritative. Unknown extra calls or
    duplicate identities are errors, never averaged or silently overwritten.
    Without one, the runner must emit explicit missing-call placeholders: truly
    absent assignments cannot be reconstructed from observations alone.
    """
    observed = {}
    for source in rows:
        row = _normalize(source)
        key = unit_key(row) + (row["arm"],)
        if key in observed:
            raise ValueError("Duplicate assignment; supply distinct stable proposal_id values")
        observed[key] = row
    assignment_mode = "runner_rows_only_absent_assignments_not_inferable"
    if expected_assignments is not None:
        assignment_mode = "explicit_expected_assignment_inventory"
        expected = {}
        for source in expected_assignments:
            row = _normalize(source, placeholder=True)
            key = unit_key(row) + (row["arm"],)
            if key in expected:
                raise ValueError("Duplicate expected assignment")
            expected[key] = row
        if set(observed) - set(expected):
            raise ValueError("Observed calls outside expected assignment inventory")
        for key, row in observed.items():
            planned = expected[key]
            for field in ("y0", "y1", "intent", "eligible"):
                if planned[field] is not None and row[field] != planned[field]:
                    raise ValueError("Observed row contradicts assignment " + field)
            expected[key] = row
        observed = expected
    prepared = sorted(observed.values(), key=lambda row: canonical(unit_key(row) + (row["arm"],)))
    # Split leakage and arm-dependent outcome labels invalidate pairing.
    task_splits, proposal_labels = {}, {}
    for row in prepared:
        task = row["task_id"]
        if task in task_splits and task_splits[task] != row["split"]:
            raise ValueError("A source task crosses development/heldout splits")
        task_splits[task] = row["split"]
        key = (task, row["cohort"], row["proposer"], row["proposal_id"])
        labels = (row["y0"], row["y1"], row["intent"], row["eligible"], tuple(sorted(row["eligibility_reasons"])))
        if key in proposal_labels and proposal_labels[key] != labels:
            raise ValueError("Reserved outcomes/intent/eligibility differ across arms, reviewers, or repeats")
        proposal_labels[key] = labels
    return prepared, assignment_mode


def accepted(row, layer):
    if layer not in LAYERS:
        raise ValueError("Unknown decision layer")
    valid_accept = row["model_valid"] and row["decision"] == "accept"
    return int(valid_accept and (layer == "reviewer_only" or not row["authenticated_failure"]))


def rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def summarize_arm(rows):
    counts = Counter(row["direction"] for row in rows)
    result = {
        "assigned": len(rows), "independent_tasks": len({row["task_id"] for row in rows}),
        "missing_rows": sum(row["_missing_row"] for row in rows),
        "valid_model_calls": sum(row["model_valid"] for row in rows),
        "invalid_or_missing_model_calls": sum(not row["model_valid"] for row in rows),
        "rows_with_authenticated_failure": sum(row["authenticated_failure"] for row in rows),
        "invalid_raw_accepts_fail_closed": sum(not row["model_valid"] and row["decision"] == "accept" for row in rows),
        "directions": {name: counts[name] for name in DIRECTIONS},
        "proposal_statuses": dict(sorted(Counter(row["proposal_status"] for row in rows).items())),
        "model_statuses": dict(sorted(Counter(str(row.get("model_status", "unspecified")) for row in rows).items())),
        "supplier_feasibility": {"fully_feasible": sum(row["supplier_feasible"] is True for row in rows),
                                 "infeasible": sum(row["supplier_feasible"] is False for row in rows),
                                 "unknown": sum(row["supplier_feasible"] is None for row in rows)},
        "eligibility_reasons": dict(sorted(Counter(reason for row in rows for reason in row["eligibility_reasons"]).items())),
        "raw_decisions": dict(sorted(Counter(row["decision"] for row in rows).items())),
        "layers": {},
    }
    for layer in LAYERS:
        acc = [accepted(row, layer) for row in rows]
        final = [row["y1"] if value else row["y0"] for row, value in zip(rows, acc)]
        by_direction = {}
        for direction in DIRECTIONS:
            selected = [(row, value) for row, value in zip(rows, acc) if row["direction"] == direction]
            naccept = sum(value for _, value in selected)
            valid = [(row, value) for row, value in selected if row["model_valid"]]
            by_direction[direction] = {
                "conditional_all_assigned": rate(naccept, len(selected)),
                "conditional_valid_calls_only": rate(sum(value for _, value in valid), len(valid)),
                "unconditional_all_assignments": rate(naccept, len(rows)),
            }
        original_correct = [(row, value) for row, value in zip(rows, final) if row["y0"] is True]
        result["layers"][layer] = {
            "acceptance_all_assigned": rate(sum(acc), len(rows)),
            "by_direction": by_direction,
            "supplier_fully_feasible_by_direction_descriptive": {
                direction: rate(sum(value for row, value in zip(rows, acc) if row["direction"] == direction and row["supplier_feasible"] is True),
                                sum(row["direction"] == direction and row["supplier_feasible"] is True for row in rows))
                for direction in DIRECTIONS},
            "final_reserved_suite_pass_among_known": rate(sum(value is True for value in final), sum(value is not None for value in final)),
            "final_reserved_suite_confirmed_pass_all_assigned": rate(sum(value is True for value in final), len(rows)),
            "final_reserved_suite_unknown": sum(value is None for value in final),
            "original_correct_preserved_among_known": rate(sum(value is True for _, value in original_correct), sum(value is not None for _, value in original_correct)),
            "original_correct_confirmed_preserved_all_initial_correct": rate(sum(value is True for _, value in original_correct), len(original_correct)),
            "original_correct_final_unknown": sum(value is None for _, value in original_correct),
        }
    return result


def exact_paired_p(positive, negative):
    """One-sided exact sign/McNemar test, favorable positive discordances.

    Each input must count independent paired source tasks, not repeated calls.
    The null gives each discordance either direction with probability one-half.
    """
    if any(type(value) is not int or value < 0 for value in (positive, negative)):
        raise ValueError("Discordances must be nonnegative integer counts")
    n = positive + negative
    if not n:
        return 1.0
    return sum(math.comb(n, j) for j in range(positive, n + 1)) / (2 ** n)


def holm_adjust(pvalues):
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in pvalues):
        raise ValueError("P-values must be finite probabilities")
    order = sorted(range(len(pvalues)), key=lambda index: (pvalues[index], index))
    result, previous = [None] * len(pvalues), 0.0
    for rank, index in enumerate(order):
        previous = max(previous, min(1.0, (len(order) - rank) * pvalues[index]))
        result[index] = previous
    return result


def _quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def paired_comparison(rows, left, right, layer, bootstrap_samples=5000, seed=DEFAULT_SEED):
    """Left-minus-right acceptance, with paired task-cluster uncertainty.

    Caller filters cohort, reviewer, split, and replicate. Missing arm rows are
    counted but cannot be paired; expected-assignment placeholders are pairable.
    Joint bootstrap samples task IDs once per draw for all outcome directions.
    Each conditional statistic retains its own clearly reported denominator.
    """
    if left == right or left not in ARMS or right not in ARMS:
        raise ValueError("Comparison requires two distinct known arms")
    if type(bootstrap_samples) is not int or bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    by_arm = {arm: {} for arm in (left, right)}
    for row in rows:
        if row["arm"] in by_arm:
            key = unit_key(row)
            if key in by_arm[row["arm"]]:
                raise ValueError("Duplicate pair unit")
            by_arm[row["arm"]][key] = row
    left_keys, right_keys = set(by_arm[left]), set(by_arm[right])
    pairs = []
    for key in sorted(left_keys & right_keys, key=canonical):
        a, b = by_arm[left][key], by_arm[right][key]
        if (a["y0"], a["y1"], a["direction"]) != (b["y0"], b["y1"], b["direction"]):
            raise ValueError("Paired reserved outcomes disagree")
        pairs.append((a, accepted(a, layer), accepted(b, layer)))
    clusters = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row, a, b in pairs:
        value = clusters[row["task_id"]][row["direction"]]
        value[0] += a - b
        value[1] += 1
    tasks = sorted(clusters)
    bootstrap = {name: [] for name in DIRECTIONS}
    rng = random.Random(derived_seed(seed, left, right, layer))
    for _ in range(bootstrap_samples):
        totals = {name: [0, 0] for name in DIRECTIONS}
        for _ in tasks:
            task = tasks[rng.randrange(len(tasks))]
            for direction, (total, n) in clusters[task].items():
                totals[direction][0] += total
                totals[direction][1] += n
        for name, (total, n) in totals.items():
            if n:
                bootstrap[name].append(total / n)
    result = {
        "left": left, "right": right, "layer": layer, "estimand": "left_minus_right_acceptance",
        "left_assigned": len(left_keys), "right_assigned": len(right_keys),
        "left_only_unpaired": len(left_keys - right_keys),
        "right_only_unpaired": len(right_keys - left_keys),
        "left_missing_assigned_rows": sum(row["_missing_row"] for row in by_arm[left].values()),
        "right_missing_assigned_rows": sum(row["_missing_row"] for row in by_arm[right].values()),
        "paired_missing_assigned_rows": sum(by_arm[left][key]["_missing_row"] or by_arm[right][key]["_missing_row"]
                                             for key in left_keys & right_keys),
        "paired_rows": len(pairs), "independent_task_clusters": len(tasks),
        "bootstrap_samples": bootstrap_samples, "bootstrap_seed": str(seed),
        "ci_method": "95% task-cluster percentile bootstrap; undefined resamples counted",
        "directions": {},
    }
    for name in DIRECTIONS:
        selected = [(row, a, b) for row, a, b in pairs if row["direction"] == name]
        cells = Counter((a, b) for _, a, b in selected)
        n = len(selected)
        independent = len({row["task_id"] for row, _, _ in selected})
        # Repeated calls/proposals/model pairs must never masquerade as sign trials.
        sign_eligible = n > 0 and independent == n and all(row["replicate"] == 0 for row, _, _ in selected)
        samples = bootstrap[name]
        result["directions"][name] = {
            "paired_rows": n, "independent_tasks": independent,
            "left_acceptance": rate(sum(a for _, a, _ in selected), n),
            "right_acceptance": rate(sum(b for _, _, b in selected), n),
            "difference": (cells[1, 0] - cells[0, 1]) / n if n else None,
            "paired_cells": {"both_accept": cells[1, 1], "left_only_accept": cells[1, 0],
                             "right_only_accept": cells[0, 1], "neither_accept": cells[0, 0]},
            "ci95": [_quantile(samples, 0.025), _quantile(samples, 0.975)] if samples else None,
            "bootstrap_defined": len(samples), "bootstrap_undefined": bootstrap_samples - len(samples),
            "exact_sign_eligible": sign_eligible,
            "one_sided_exact_p": exact_paired_p(cells[1, 0], cells[0, 1]) if sign_eligible else None,
        }
    return result


def _negate_summary(summary):
    return {"difference": -summary["difference"] if summary["difference"] is not None else None,
            "ci95": [-summary["ci95"][1], -summary["ci95"][0]] if summary["ci95"] is not None else None,
            "paired_rows": summary["paired_rows"], "independent_tasks": summary["independent_tasks"]}


def _comparison_gates(uniform, edit, h2_adjusted_p, selection=None):
    harm = uniform["directions"]["harmful"]
    useful = _negate_summary(uniform["directions"]["useful"])
    edit_harm = edit["directions"]["harmful"]
    complete = not any(comparison[name] for comparison in (uniform, edit)
                       for name in ("left_only_unpaired", "right_only_unpaired"))
    required = {"uniform_hybrid": uniform, "edit_hybrid": edit}
    if selection is not None:
        required["selected_uniform_witness"] = selection
    missing_counts = {name: comparison["left_missing_assigned_rows"] + comparison["right_missing_assigned_rows"]
                      for name, comparison in required.items()}
    observed_complete = not any(missing_counts.values())
    harm_pass = (harm["difference"] is not None and harm["difference"] >= 0.05
                 and harm["ci95"] is not None and harm["ci95"][0] > 0)
    useful_pass = useful["ci95"] is not None and useful["ci95"][0] > -0.05
    useful_source = uniform["directions"]["useful"]
    useful_zero = (useful_source["paired_rows"] > 0
                   and useful_source["paired_cells"]["left_only_accept"] == 0
                   and useful_source["paired_cells"]["right_only_accept"] == 0)
    adequate = harm["independent_tasks"] >= 40 and useful["independent_tasks"] >= 40
    edit_direction = edit_harm["difference"] is not None and edit_harm["difference"] > 0
    edit_ci = edit_harm["ci95"] is not None and edit_harm["ci95"][0] > 0
    return {
        "harm_reduction_uniform_minus_hybrid": {key: harm[key] for key in ("difference", "ci95", "paired_rows", "independent_tasks")},
        "useful_acceptance_hybrid_minus_uniform": useful,
        "harm_reduction_edit_minus_hybrid": {key: edit_harm[key] for key in ("difference", "ci95", "paired_rows", "independent_tasks")},
        "complete_arm_pairing": complete,
        "missing_assigned_rows_per_required_comparison": missing_counts,
        "complete_required_assigned_observations": observed_complete,
        "harm_reduction_at_least_005_and_ci_excludes_zero": harm_pass,
        "useful_noninferiority_ci_lower_above_minus_005": useful_pass,
        "useful_all_zero_paired_differences": useful_zero,
        "useful_noninferiority_population_claim_supported": useful_pass and adequate and not useful_zero,
        "minimum_40_harmful_and_40_useful_tasks": adequate,
        "recommendation_adequacy": adequate and not useful_zero,
        "h2_holm4_below_005": h2_adjusted_p < 0.05,
        "static_edit_directional_benefit": edit_direction,
        "static_edit_ci_excludes_zero": edit_ci,
        "numerical_policy_criteria_met": complete and harm_pass and useful_pass and h2_adjusted_p < 0.05 and edit_direction,
        "bounded_policy_criteria_met": complete and observed_complete and harm_pass and useful_pass and h2_adjusted_p < 0.05 and edit_direction and adequate and not useful_zero,
        "degeneracy_interpretation": "An all-zero useful paired contrast has a degenerate empirical bootstrap; CI[0,0] is retained but does not prove population noninferiority.",
        "interpretation": "Criteria concern these frozen static comparators only; directional edit benefit is not demonstrated superiority over coverage/differential testing or broad testing state of the art.",
    }


def analyze(rows, reviewers, expected_assignments=None, bootstrap_samples=5000, seed=DEFAULT_SEED):
    """Build counts, four heldout primary hypotheses, and secondary comparisons.

    reviewers must contain exactly the two prospectively frozen IDs. Absent or
    non-sign-eligible primary comparisons receive p=1 in the unchanged Holm-4
    family. No development outcomes or stability replicates enter primary tests.
    """
    reviewers = tuple(reviewers)
    if len(reviewers) != 2 or len(set(reviewers)) != 2 or any(not isinstance(x, str) or not x for x in reviewers):
        raise ValueError("Exactly two distinct frozen reviewer IDs are required")
    rows, assignment_mode = prepare_rows(rows, expected_assignments)
    if {row["reviewer"] for row in rows} - set(reviewers):
        raise ValueError("Unexpected reviewer outside frozen hypothesis family")
    grouping = ("split", "cohort", "reviewer", "proposer", "intent", "arm", "replicate", "eligible")
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[name] for name in grouping)].append(row)
    summaries = [{"group": dict(zip(grouping, key)), **summarize_arm(value)}
                 for key, value in sorted(groups.items(), key=lambda item: canonical(item[0]))]
    comparisons, hypotheses, lookup = [], [], {}
    for reviewer in reviewers:
        primary_rows = [row for row in rows if row["split"] == "heldout" and row["cohort"] == "native"
                        and row["reviewer"] == reviewer and row["replicate"] == 0 and row["eligible"] is True]
        for left, right in (("selected_w", "uniform_w"), ("uniform_a", "hybrid"), ("edit", "hybrid")):
            for layer in LAYERS:
                comp = paired_comparison(primary_rows, left, right, layer, bootstrap_samples,
                                         canonical((seed, "heldout", "native", reviewer)))
                comp.update(split="heldout", cohort="native", reviewer=reviewer, replicate=0, eligible=True)
                comparisons.append(comp)
                lookup[reviewer, left, right, layer] = comp
        for name, left, right, layer in (("H1", "selected_w", "uniform_w", "reviewer_only"),
                                         ("H2", "uniform_a", "hybrid", "enforced")):
            comparison = lookup[reviewer, left, right, layer]
            result = comparison["directions"]["harmful"]
            pvalue = result["one_sided_exact_p"]
            complete = not (comparison["left_only_unpaired"] or comparison["right_only_unpaired"])
            eligible = result["exact_sign_eligible"] and complete
            hypotheses.append({"hypothesis": name, "reviewer": reviewer, "layer": layer,
                               "contrast": left + " minus " + right, "direction": "harmful",
                               "estimand": "positive acceptance difference", "analysis_eligible": eligible,
                               "reason_if_ineligible": None if eligible else "missing pairing, empty cohort, or multiple observations per task",
                               "difference": result["difference"], "ci95": result["ci95"],
                               "paired_rows": result["paired_rows"], "independent_tasks": result["independent_tasks"],
                               "raw_one_sided_exact_p": pvalue,
                               "family_p": pvalue if eligible else 1.0})
    for hypothesis, adjusted in zip(hypotheses, holm_adjust([item["family_p"] for item in hypotheses])):
        hypothesis["holm4_adjusted_p"] = adjusted
        hypothesis["reject_at_005"] = hypothesis["analysis_eligible"] and adjusted < 0.05
    gates = []
    for reviewer in reviewers:
        adjusted = next(item["holm4_adjusted_p"] for item in hypotheses if item["reviewer"] == reviewer and item["hypothesis"] == "H2")
        gates.append({"reviewer": reviewer, **_comparison_gates(
            lookup[reviewer, "uniform_a", "hybrid", "enforced"],
            lookup[reviewer, "edit", "hybrid", "enforced"], adjusted,
            lookup[reviewer, "selected_w", "uniform_w", "reviewer_only"])})
    # Generated cohorts remain intent/proposer-specific descriptive transfer.
    generated_groups = defaultdict(list)
    for row in rows:
        if row["cohort"] == "generated" and row["replicate"] == 0 and row["eligible"] is True:
            generated_groups[(row["split"], row["reviewer"], row["proposer"], row["intent"])].append(row)
    generated = []
    for key, subset in sorted(generated_groups.items(), key=lambda item: canonical(item[0])):
        for left, right in (("selected_w", "uniform_w"), ("uniform_a", "hybrid"), ("edit", "hybrid")):
            for layer in LAYERS:
                comp = paired_comparison(subset, left, right, layer, bootstrap_samples,
                                         canonical((seed, "generated", key)))
                comp.update(dict(zip(("split", "reviewer", "proposer", "intent"), key)))
                comp.update(cohort="generated", replicate=0, eligible=True, inferential_role="secondary_descriptive_not_Holm4",
                            interpretation="Model-proposed revisions; intentional corruption is not naturally occurring model error. Missing intent is unclassified.")
                generated.append(comp)
    return {
        "schema_version": SCHEMA_VERSION,
        "configuration": {"reviewers": list(reviewers), "primary_split": "heldout", "primary_replicate": 0,
                          "bootstrap_samples": bootstrap_samples, "seed": str(seed), "holm_family_size": 4,
                          "harm_margin": 0.05, "useful_noninferiority_margin": -0.05,
                          "recommendation_minimum_tasks_per_direction": 40},
        "accounting": {"assignment_mode": assignment_mode, "assigned_rows": len(rows),
                       "independent_source_tasks": len({row["task_id"] for row in rows}),
                       "missing_rows_materialized": sum(row["_missing_row"] for row in rows),
                       "replicate_rows_secondary_only": sum(row["replicate"] != 0 for row in rows),
                       "unknown_reserved_outcome_rows": sum(row["direction"] == "unknown" for row in rows),
                       "eligible_rows": sum(row["eligible"] is True for row in rows),
                       "ineligible_rows": sum(row["eligible"] is False for row in rows),
                       "eligibility_undeclared_rows": sum(row["eligible"] is None for row in rows),
                       "generated_intent_missing_rows": sum(row["cohort"] == "generated" and row["intent"] is None for row in rows)},
        "interpretation": [
            "Reserved-suite passing is a finite outcome oracle, not proof of semantic correctness.",
            "H1 measures reviewer-only response to evidence selection; H2 measures enforced outcomes.",
            "All assigned direction-conditional rates retain invalid/missing model calls as non-acceptance; valid-call-only rates are separately labeled.",
            "Unknown reserved outcomes remain assigned but cannot be labeled harmful/useful.",
            "Only explicitly eligible=true rows enter primary and generated transfer contrasts; ineligible/undeclared rows and reasons remain in full assigned arm counts.",
            "Bootstrap units are source tasks, not calls, proposals, models, or repetitions; reviewers remain separate.",
            "Development results and nonzero replicates are descriptive; exact primary tests use only heldout native replicate zero.",
            "Failing authenticated evidence vetoes acceptance in every arm; logical veto behavior alone is not a novel empirical defense result.",
        ],
        "arm_summaries": summaries, "primary_hypotheses": hypotheses,
        "native_primary_comparisons": comparisons, "policy_gates": gates,
        "generated_secondary_comparisons": generated,
        "stability": stability_report(rows),
    }


def stability_report(rows):
    primary = {(unit_key(row)[:-1], row["arm"]): row for row in rows if row["replicate"] == 0}
    repeated = [row for row in rows if row["replicate"] != 0]
    groups = defaultdict(list)
    unmatched = 0
    for row in repeated:
        original = primary.get((unit_key(row)[:-1], row["arm"]))
        if original is None:
            unmatched += 1
            continue
        groups[(row["split"], row["cohort"], row["reviewer"], row["arm"], row["replicate"])].append((original, row))
    results = []
    for key, pairs in sorted(groups.items(), key=lambda item: canonical(item[0])):
        results.append({"group": dict(zip(("split", "cohort", "reviewer", "arm", "replicate"), key)),
                        "paired_calls": len(pairs), "independent_tasks": len({a["task_id"] for a, _ in pairs}),
                        "layers": {layer: {"acceptance_agreement": rate(sum(accepted(a, layer) == accepted(b, layer) for a, b in pairs), len(pairs)),
                                            "both_model_calls_valid": sum(a["model_valid"] and b["model_valid"] for a, b in pairs)}
                                   for layer in LAYERS}})
    return {"unmatched_repeat_rows": unmatched, "groups": results,
            "interpretation": "Within-assignment repeat stability only; repetitions never enlarge the independent task count or primary test family."}


def render_markdown(report):
    def value(number):
        return "undefined" if number is None else f"{number:.4f}"

    lines = ["# Prospective code-study analysis", "", report["schema_version"], "",
             f"Assigned decision rows: {report['accounting']['assigned_rows']}; independent source tasks: {report['accounting']['independent_source_tasks']}.",
             f"Assignment accounting: `{report['accounting']['assignment_mode']}`.", "",
             "Primary tests use heldout native proposals, replicate zero. Differences are proportions. Confidence intervals are 95% task-cluster percentile intervals.", "",
             "| Hypothesis | Reviewer | Layer | Difference | CI | Holm-4 p | Eligible |", "|---|---|---|---:|---|---:|---|"]
    for row in report["primary_hypotheses"]:
        ci = "undefined" if row["ci95"] is None else "[" + ", ".join(value(x) for x in row["ci95"]) + "]"
        lines.append(f"| {row['hypothesis']} | {row['reviewer']} | {row['layer']} | {value(row['difference'])} | {ci} | {value(row['holm4_adjusted_p'])} | {row['analysis_eligible']} |")
    lines.extend(["", "H1: selected witness minus uniform witness harmful acceptance, reviewer only. H2: uniform verification minus hybrid verification harmful acceptance, enforced.", "",
                  "| Reviewer | Harm margin + CI | Useful CI criterion | >=40 H and U | Useful all-zero | Static edit direction | Bounded policy criteria |",
                  "|---|---|---|---|---|---|---|"])
    for row in report["policy_gates"]:
        lines.append(f"| {row['reviewer']} | {row['harm_reduction_at_least_005_and_ci_excludes_zero']} | {row['useful_noninferiority_ci_lower_above_minus_005']} | {row['minimum_40_harmful_and_40_useful_tasks']} | {row['useful_all_zero_paired_differences']} | {row['static_edit_directional_benefit']} | {row['bounded_policy_criteria_met']} |")
    lines.extend(["", "An all-zero useful paired contrast produces a degenerate empirical interval. Its numerical CI is retained, but does not establish population noninferiority or pass the recommendation gate."])
    lines.extend(["", "Arm counts below keep missing/invalid calls in assigned denominators. H/U are harmful/useful assigned rows; unknown outcomes are separate.", "",
                  "| Split/cohort | Reviewer | Proposer/intent | Arm/replicate | Eligible | Assigned | Valid | H/U/unknown | Reviewer accepts | Enforced accepts |",
                  "|---|---|---|---|---|---:|---:|---|---|---|"])
    for row in report["arm_summaries"]:
        group, directions = row["group"], row["directions"]
        accepts = [row["layers"][layer]["acceptance_all_assigned"] for layer in LAYERS]
        lines.append(f"| {group['split']}/{group['cohort']} | {group['reviewer']} | {group['proposer']}/{group['intent']} | {group['arm']}/{group['replicate']} | {group['eligible']} | {row['assigned']} | {row['valid_model_calls']} | {directions['harmful']}/{directions['useful']}/{directions['unknown']} | {accepts[0]['numerator']}/{accepts[0]['denominator']} | {accepts[1]['numerator']}/{accepts[1]['denominator']} |")
    lines.extend(["", "Machine-readable output also contains paired cell counts, conditional/all-assigned/valid-only denominators, final reserved-suite outcomes, generated intent-specific transfer contrasts, and repeat stability.", ""])
    lines.extend("- " + note for note in report["interpretation"])
    lines.extend(["", "A met gate is bounded evidence for this protocol. It is not a novelty certificate or broad superiority over established regression/differential testing.", ""])
    return "\n".join(lines)


def load_jsonl_bytes(data, source="<bytes>"):
    rows = []
    for number, line in enumerate(data.decode("utf-8-sig").splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON constant: " + x)))
            except ValueError as exc:
                raise ValueError(f"{source}:{number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{source}:{number}: expected an object")
            rows.append(row)
    return rows


def load_jsonl(path):
    return load_jsonl_bytes(Path(path).read_bytes(), str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decisions")
    parser.add_argument("--reviewer", action="append", required=True)
    parser.add_argument("--expected-assignments")
    parser.add_argument("--frozen-protocol", required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    args = parser.parse_args()
    protocol_hash = hashlib.sha256(Path(args.frozen_protocol).read_bytes()).hexdigest()
    if protocol_hash != args.expected_protocol_sha256.lower():
        raise ValueError("Frozen protocol hash mismatch; do not inspect model outcomes")
    decision_bytes = Path(args.decisions).read_bytes()
    expected_bytes = Path(args.expected_assignments).read_bytes() if args.expected_assignments else None
    expected = load_jsonl_bytes(expected_bytes, args.expected_assignments) if expected_bytes is not None else None
    report = analyze(load_jsonl_bytes(decision_bytes, args.decisions), args.reviewer, expected)
    report["provenance"] = {
        "frozen_protocol_sha256": protocol_hash,
        "decisions_sha256": hashlib.sha256(decision_bytes).hexdigest(),
        "expected_assignments_sha256": hashlib.sha256(expected_bytes).hexdigest() if expected_bytes is not None else None,
        "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    Path(args.output_json).write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    Path(args.output_markdown).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
