"""Separate stdlib recomputation of frozen study counts and gate arithmetic.

No import of the study's analysis, selectors, scorer, or runner is permitted.
This implementation was written by the frozen-analysis author; independent
authorship/review is supplied by the parent reviewer's separate controls.

Reserved outcome labels and authenticity flags are input assertions checked by
the surrounding artifact auditor. Published bootstrap intervals are numerical
inputs here: their recomputation and population coverage are NOT certified.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import math
import json

REVIEWERS = ("qwen.qwen3-coder-next", "mistral.devstral-2-123b")
LAYERS = ("reviewer_only", "enforced")
DIRECTIONS = ("harmful", "useful", "other", "unknown")
MODEL_ID = ("task_id", "split", "cohort", "reviewer", "proposer", "proposal_id", "replicate", "arm")
MODEL_GROUP = ("split", "cohort", "reviewer", "proposer", "intent", "arm", "replicate", "eligible")
OFFLINE_ID = ("task_id", "split", "cohort", "proposer", "intent", "proposal_id", "replicate", "budget", "policy")
OFFLINE_GROUP = ("split", "cohort", "proposer", "intent", "direction", "budget", "policy", "eligible")
SEEDS = set(range(20))


def equivalent(actual, expected):
    """Exact categorical/count equality; small serialization tolerance for rates."""
    if expected is None or isinstance(expected, (str, bool, int)):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, float):
        return type(actual) in (float, int) and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(equivalent(actual[k], v) for k, v in expected.items())
    if isinstance(expected, (tuple, list)):
        return isinstance(actual, (tuple, list)) and len(actual) == len(expected) and all(equivalent(a, b) for a, b in zip(actual, expected))
    return actual == expected


class Checks:
    def __init__(self):
        self.rows = []

    def same(self, name, actual, expected):
        passed = equivalent(actual, expected)
        detail = "" if passed else ("expected=" + repr(expected) + "; observed=" + repr(actual))[:700]
        self.rows.append({"check": name, "passed": passed, "detail": detail})

    def condition(self, name, passed, detail):
        self.rows.append({"check": name, "passed": bool(passed), "detail": "" if passed else str(detail)[:700]})

    def subset(self, name, actual, expected):
        # Compare only independently recomputed fields; numerical CIs and prose
        # are deliberately outside this operation unless explicitly specified.
        self.condition(name + ".object", isinstance(actual, dict), "Expected a result object")
        if not isinstance(actual, dict):
            return
        for field, value in expected.items():
            self.same(name + "." + field, actual.get(field), value)


def fraction(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def binomial_tail(favorable, unfavorable):
    """Exact rational recurrence, independently specified from binomial PMF."""
    if type(favorable) is not int or type(unfavorable) is not int or min(favorable, unfavorable) < 0:
        raise ValueError("Discordances must be nonnegative integer source-task counts")
    n = favorable + unfavorable
    term = Fraction(1, 2 ** n)
    total = Fraction(0)
    for j in range(n + 1):
        if j >= favorable:
            total += term
        if j < n:
            term = term * Fraction(n - j, j + 1)
    return float(total)


def holm_four(values):
    if len(values) != 4 or any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in values):
        raise ValueError("Exactly four finite primary p-values are required")
    ranked = sorted((p, i) for i, p in enumerate(values))
    adjusted = [None] * 4
    for position, (_, original_index) in enumerate(ranked):
        adjusted[original_index] = min(1.0, max((4 - rank) * ranked[rank][0] for rank in range(position + 1)))
    return adjusted


def direction(row):
    left, right = row.get("y0"), row.get("y1")
    if any(value is not None and type(value) is not bool for value in (left, right)):
        raise ValueError("Reserved outcomes must be bool/null")
    if left is None or right is None:
        return "unknown"
    if left is True and right is False:
        return "harmful"
    if left is False and right is True:
        return "useful"
    return "other"


def row_key(row, fields):
    return tuple(row[name] for name in fields)


def join_assignments(observed, expected, offline=False):
    """Expected inventory defines every assignment; no complete-case deletion."""
    fields = OFFLINE_ID if offline else MODEL_ID

    def normalize(source):
        row = dict(source)
        if type(row.get("task_id")) not in (str, int):
            raise ValueError("Invalid task ID")
        row["task_id"] = str(row["task_id"])
        row.setdefault("proposer", None)
        row.setdefault("intent", None)
        row.setdefault("eligible", None)
        row.setdefault("eligibility_reasons", [] if row["eligible"] is not None or offline else ["eligibility_not_declared"])
        row.setdefault("supplier_feasible", None)
        row.setdefault("_missing_row", False)
        if row["split"] not in ("dev", "heldout") or row["cohort"] not in ("native", "generated"):
            raise ValueError("Invalid split/cohort")
        if row["eligible"] is not None and type(row["eligible"]) is not bool:
            raise ValueError("Eligibility must be Boolean/null")
        if type(row["replicate"]) is not int or row["replicate"] < 0:
            raise ValueError("Invalid replicate")
        if row["supplier_feasible"] is not None and type(row["supplier_feasible"]) is not bool:
            raise ValueError("Supplier feasibility must be bool/null")
        if not isinstance(row["eligibility_reasons"], list) or any(not isinstance(x, str) for x in row["eligibility_reasons"]):
            raise ValueError("Eligibility reasons must be string list")
        if any(row[name] is not None and not isinstance(row[name], str) for name in ("proposer", "intent")):
            raise ValueError("Proposer and intent must be string/null")
        if not offline:
            if row["reviewer"] not in REVIEWERS or row["arm"] not in ("no_witness", "uniform_w", "selected_w", "uniform_a", "fixed", "edit", "complement", "hybrid"):
                raise ValueError("Reviewer/arm outside frozen study")
            row.setdefault("y0", None)
            row.setdefault("y1", None)
            true_direction = direction(row)
            if row.get("direction", true_direction) not in (true_direction, "other" if true_direction == "unknown" else true_direction):
                raise ValueError("Direction contradicts reserved outcomes")
            row["direction"] = true_direction
            row.setdefault("proposal_id", "direction:" + true_direction)
        elif row["direction"] not in DIRECTIONS:
            raise ValueError("Invalid offline direction")
        if offline and (row["policy"] not in ("fixed", "uniform", "edit", "complement", "hybrid")
                        or type(row["budget"]) is not int or row["budget"] < 0 or type(row["eligible"]) is not bool):
            raise ValueError("Invalid offline policy/budget/eligibility")
        if not isinstance(row["proposal_id"], str) or not row["proposal_id"]:
            raise ValueError("Stable nonempty proposal ID required")
        return row

    assignments = {}
    for source in expected:
        row = normalize(source)
        key = row_key(row, fields)
        if key in assignments:
            raise ValueError("Duplicate expected assignment: " + repr(key))
        assignments[key] = row
    seen = set()
    for source in observed:
        row = normalize(source)
        key = row_key(row, fields)
        if key not in assignments or key in seen:
            raise ValueError("Unexpected or duplicate observed assignment: " + repr(key))
        base = assignments[key]
        metadata = ("eligible", "direction", "intent", "eligibility_reasons") if offline else ("eligible", "intent", "y0", "y1")
        for name in metadata:
            if name in base and base[name] is not None and row.get(name) != base[name]:
                raise ValueError("Observed metadata contradicts expected assignment: " + name)
        assignments[key] = row
        seen.add(key)
    for key, row in assignments.items():
        if key not in seen:
            row["_missing_row"] = True
            if offline:
                row.update(detected=None, logical_supplier_executions=None, logical_independent_executions=None)
            else:
                row.update(model_valid=False, decision="abstain", authenticated_failure=False)
                row.setdefault("proposal_status", "unobserved")
        if offline:
            if row.get("detected") is not None and type(row["detected"]) is not bool:
                raise ValueError("Detected must be bool/null")
            for name in ("logical_supplier_executions", "logical_independent_executions"):
                value = row.get(name)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("Invalid logical execution cost")
        elif (type(row.get("model_valid")) is not bool or type(row.get("authenticated_failure")) is not bool
              or row.get("decision") not in ("accept", "keep", "abstain")):
            raise ValueError("Invalid decision/validity/authentication input")
    # Metadata must agree across arms and repeats for the same proposal.
    splits, labels = {}, {}
    for row in assignments.values():
        task = row["task_id"]
        if task in splits and splits[task] != row["split"]:
            raise ValueError("One source task crosses development and heldout")
        splits[task] = row["split"]
        key = (task, row["cohort"], row["proposer"], row["proposal_id"])
        label = (row["direction"], row["eligible"], row["intent"], row.get("y0"), row.get("y1"), tuple(sorted(row["eligibility_reasons"])))
        if key in labels and labels[key] != label:
            raise ValueError("Proposal metadata changes across arms or repetitions")
        labels[key] = label
    return list(assignments.values())


def accept(row, layer):
    if layer not in LAYERS:
        raise ValueError("Invalid decision layer")
    return int(row["model_valid"] is True and row["decision"] == "accept"
               and (layer == "reviewer_only" or row["authenticated_failure"] is False))


def arm_counts(rows):
    count = len(rows)
    result = {
        "assigned": count, "independent_tasks": len({r["task_id"] for r in rows}),
        "missing_rows": sum(r["_missing_row"] for r in rows),
        "valid_model_calls": sum(r["model_valid"] for r in rows),
        "invalid_or_missing_model_calls": sum(not r["model_valid"] for r in rows),
        "rows_with_authenticated_failure": sum(r["authenticated_failure"] for r in rows),
        "invalid_raw_accepts_fail_closed": sum(not r["model_valid"] and r["decision"] == "accept" for r in rows),
        "directions": {d: sum(r["direction"] == d for r in rows) for d in DIRECTIONS},
        "proposal_statuses": dict(Counter(r["proposal_status"] for r in rows)),
        "model_statuses": dict(Counter(str(r.get("model_status", "unspecified")) for r in rows)),
        "eligibility_reasons": dict(Counter(reason for r in rows for reason in r["eligibility_reasons"])),
        "raw_decisions": dict(Counter(r["decision"] for r in rows)),
        "supplier_feasibility": {"fully_feasible": sum(r["supplier_feasible"] is True for r in rows),
                                 "infeasible": sum(r["supplier_feasible"] is False for r in rows),
                                 "unknown": sum(r["supplier_feasible"] is None for r in rows)},
        "layers": {},
    }
    for layer in LAYERS:
        outcomes = [r["y1"] if accept(r, layer) else r["y0"] for r in rows]
        original = [outcome for r, outcome in zip(rows, outcomes) if r["y0"] is True]
        by_direction, feasible = {}, {}
        for d in DIRECTIONS:
            selected = [r for r in rows if r["direction"] == d]
            valid = [r for r in selected if r["model_valid"]]
            feas = [r for r in selected if r["supplier_feasible"] is True]
            n = sum(accept(r, layer) for r in selected)
            by_direction[d] = {"conditional_all_assigned": fraction(n, len(selected)),
                               "conditional_valid_calls_only": fraction(sum(accept(r, layer) for r in valid), len(valid)),
                               "unconditional_all_assignments": fraction(n, count)}
            feasible[d] = fraction(sum(accept(r, layer) for r in feas), len(feas))
        result["layers"][layer] = {
            "acceptance_all_assigned": fraction(sum(accept(r, layer) for r in rows), count),
            "by_direction": by_direction, "supplier_fully_feasible_by_direction_descriptive": feasible,
            "final_reserved_suite_pass_among_known": fraction(sum(x is True for x in outcomes), sum(x is not None for x in outcomes)),
            "final_reserved_suite_confirmed_pass_all_assigned": fraction(sum(x is True for x in outcomes), count),
            "final_reserved_suite_unknown": sum(x is None for x in outcomes),
            "original_correct_preserved_among_known": fraction(sum(x is True for x in original), sum(x is not None for x in original)),
            "original_correct_confirmed_preserved_all_initial_correct": fraction(sum(x is True for x in original), len(original)),
            "original_correct_final_unknown": sum(x is None for x in original),
        }
    return result


def paired_counts(rows, left, right, layer):
    arms = {arm: {} for arm in (left, right)}
    for row in rows:
        if row["arm"] in arms:
            key = row_key(row, MODEL_ID[:-1])
            if key in arms[row["arm"]]:
                raise ValueError("Duplicate model pair")
            arms[row["arm"]][key] = row
    akeys, bkeys = set(arms[left]), set(arms[right])
    common = akeys & bkeys
    result = {
        "left": left, "right": right, "layer": layer,
        "left_assigned": len(akeys), "right_assigned": len(bkeys),
        "left_only_unpaired": len(akeys - bkeys), "right_only_unpaired": len(bkeys - akeys),
        "left_missing_assigned_rows": sum(r["_missing_row"] for r in arms[left].values()),
        "right_missing_assigned_rows": sum(r["_missing_row"] for r in arms[right].values()),
        "paired_missing_assigned_rows": sum(arms[left][k]["_missing_row"] or arms[right][k]["_missing_row"] for k in common),
        "paired_rows": len(common), "independent_task_clusters": len({k[0] for k in common}),
        "directions": {},
    }
    for d in DIRECTIONS:
        pairs = [(arms[left][k], arms[right][k]) for k in common if arms[left][k]["direction"] == d]
        cells = Counter((accept(a, layer), accept(b, layer)) for a, b in pairs)
        n, tasks = len(pairs), len({a["task_id"] for a, _ in pairs})
        sign_ok = n > 0 and n == tasks and all(a["replicate"] == 0 for a, _ in pairs)
        result["directions"][d] = {
            "paired_rows": n, "independent_tasks": tasks,
            "left_acceptance": fraction(cells[1, 0] + cells[1, 1], n),
            "right_acceptance": fraction(cells[0, 1] + cells[1, 1], n),
            "difference": (cells[1, 0] - cells[0, 1]) / n if n else None,
            "paired_cells": {"both_accept": cells[1, 1], "left_only_accept": cells[1, 0],
                             "right_only_accept": cells[0, 1], "neither_accept": cells[0, 0]},
            "exact_sign_eligible": sign_ok,
            "one_sided_exact_p": binomial_tail(cells[1, 0], cells[0, 1]) if sign_ok else None,
        }
    return result


def index_public(items, key):
    output = {}
    for item in items:
        identity = key(item)
        if identity in output:
            raise ValueError("Duplicate public result identity: " + repr(identity))
        output[identity] = item
    return output


def check_ci(checks, name, ci, n):
    valid = ci is None if n == 0 else (
        isinstance(ci, list) and len(ci) == 2 and all(type(x) in (int, float) and math.isfinite(x) for x in ci)
        and -1 <= ci[0] <= ci[1] <= 1)
    checks.condition(name + ".published_ci_shape_only", valid,
                     "Invalid published CI shape/range; no independent bootstrap recomputation")
    return ci if valid and ci is not None else None


def audit_models(rows, report, checks):
    checks.subset("model.configuration", report.get("configuration"), {
        "reviewers": list(REVIEWERS), "primary_split": "heldout", "primary_replicate": 0,
        "bootstrap_samples": 5000, "seed": "praxis008-analysis-v1", "holm_family_size": 4,
        "harm_margin": .05, "useful_noninferiority_margin": -.05, "recommendation_minimum_tasks_per_direction": 40})
    checks.subset("model.accounting", report.get("accounting"), {
        "assignment_mode": "explicit_expected_assignment_inventory", "assigned_rows": len(rows),
        "independent_source_tasks": len({r["task_id"] for r in rows}),
        "missing_rows_materialized": sum(r["_missing_row"] for r in rows),
        "replicate_rows_secondary_only": sum(r["replicate"] != 0 for r in rows),
        "unknown_reserved_outcome_rows": sum(r["direction"] == "unknown" for r in rows),
        "eligible_rows": sum(r["eligible"] is True for r in rows),
        "ineligible_rows": sum(r["eligible"] is False for r in rows),
        "eligibility_undeclared_rows": sum(r["eligible"] is None for r in rows),
        "generated_intent_missing_rows": sum(r["cohort"] == "generated" and r["intent"] is None for r in rows)})
    grouped = defaultdict(list)
    for row in rows:
        grouped[row_key(row, MODEL_GROUP)].append(row)
    published = index_public(report["arm_summaries"], lambda item: row_key(item["group"], MODEL_GROUP))
    checks.same("model.arm_group_coverage", sorted(map(repr, published)), sorted(map(repr, grouped)))
    for key in published.keys() & grouped.keys():
        checks.subset("model.arm." + repr(key), published[key], arm_counts(grouped[key]))
    comp_index = index_public(report["native_primary_comparisons"], lambda x: (x["reviewer"], x["left"], x["right"], x["layer"]))
    expected_comps = {}
    for reviewer in REVIEWERS:
        subset = [r for r in rows if r["cohort"] == "native" and r["split"] == "heldout" and r["replicate"] == 0 and r["eligible"] is True and r["reviewer"] == reviewer]
        for a, b in (("selected_w", "uniform_w"), ("uniform_a", "hybrid"), ("edit", "hybrid")):
            for layer in LAYERS:
                key = reviewer, a, b, layer
                expected_comps[key] = paired_counts(subset, a, b, layer)
    checks.same("model.native_comparison_coverage", sorted(map(repr, comp_index)), sorted(map(repr, expected_comps)))
    cis = {}
    for key in comp_index.keys() & expected_comps.keys():
        observed, expected = comp_index[key], expected_comps[key]
        checks.subset("model.native." + repr(key), observed, {k: v for k, v in expected.items() if k != "directions"})
        checks.subset("model.native_scope." + repr(key), observed, {"split": "heldout", "cohort": "native", "replicate": 0, "eligible": True})
        for d in DIRECTIONS:
            checks.subset("model.native." + repr(key) + "." + d, observed["directions"][d], expected["directions"][d])
            cis[key, d] = check_ci(checks, "model.native." + repr(key) + "." + d,
                                  observed["directions"][d].get("ci95"), expected["directions"][d]["paired_rows"])
    hypotheses = []
    for reviewer in REVIEWERS:
        for h, a, b, layer in (("H1", "selected_w", "uniform_w", "reviewer_only"), ("H2", "uniform_a", "hybrid", "enforced")):
            key = reviewer, a, b, layer
            c = expected_comps[key]
            d = c["directions"]["harmful"]
            eligible = d["exact_sign_eligible"] and c["left_only_unpaired"] == c["right_only_unpaired"] == 0
            hypotheses.append({"hypothesis": h, "reviewer": reviewer, "layer": layer, "contrast": a + " minus " + b,
                               "direction": "harmful", "analysis_eligible": eligible,
                               "difference": d["difference"], "ci95": cis.get((key, "harmful")),
                               "paired_rows": d["paired_rows"], "independent_tasks": d["independent_tasks"],
                               "raw_one_sided_exact_p": d["one_sided_exact_p"],
                               "family_p": d["one_sided_exact_p"] if eligible else 1.0})
    for row, adjusted in zip(hypotheses, holm_four([x["family_p"] for x in hypotheses])):
        row.update(holm4_adjusted_p=adjusted, reject_at_005=row["analysis_eligible"] and adjusted < .05)
    public_h = index_public(report["primary_hypotheses"], lambda x: (x["reviewer"], x["hypothesis"]))
    checks.same("model.primary_family_coverage", sorted(public_h), sorted((x["reviewer"], x["hypothesis"]) for x in hypotheses))
    for row in hypotheses:
        checks.subset("model.primary." + row["reviewer"] + "." + row["hypothesis"], public_h.get((row["reviewer"], row["hypothesis"])), row)
    public_g = index_public(report["policy_gates"], lambda x: x["reviewer"])
    checks.same("model.policy_gate_coverage", sorted(public_g), sorted(REVIEWERS))
    for reviewer in REVIEWERS:
        uniform_key = reviewer, "uniform_a", "hybrid", "enforced"
        edit_key = reviewer, "edit", "hybrid", "enforced"
        selection_key = reviewer, "selected_w", "uniform_w", "reviewer_only"
        uniform, edit, selection = (expected_comps[k] for k in (uniform_key, edit_key, selection_key))
        harm, useful, eharm = uniform["directions"]["harmful"], uniform["directions"]["useful"], edit["directions"]["harmful"]
        hci, uci, eci = cis.get((uniform_key, "harmful")), cis.get((uniform_key, "useful")), cis.get((edit_key, "harmful"))
        useful_ci = [-uci[1], -uci[0]] if uci is not None else None
        useful_diff = -useful["difference"] if useful["difference"] is not None else None
        complete = all(c["left_only_unpaired"] == c["right_only_unpaired"] == 0 for c in (uniform, edit))
        missing = {name: c["left_missing_assigned_rows"] + c["right_missing_assigned_rows"] for name, c in
                   (("uniform_hybrid", uniform), ("edit_hybrid", edit), ("selected_uniform_witness", selection))}
        observed = all(n == 0 for n in missing.values())
        adequacy = harm["independent_tasks"] >= 40 and useful["independent_tasks"] >= 40
        zero = useful["paired_rows"] > 0 and useful["paired_cells"]["left_only_accept"] == useful["paired_cells"]["right_only_accept"] == 0
        harm_ok = harm["difference"] is not None and harm["difference"] >= .05 and hci is not None and hci[0] > 0
        useful_ok = useful_ci is not None and useful_ci[0] > -.05
        edit_ok = eharm["difference"] is not None and eharm["difference"] > 0
        p_ok = next(h["holm4_adjusted_p"] for h in hypotheses if h["reviewer"] == reviewer and h["hypothesis"] == "H2") < .05
        def compact(d, ci, value=None):
            return {"difference": d["difference"] if value is None else value, "ci95": ci,
                    "paired_rows": d["paired_rows"], "independent_tasks": d["independent_tasks"]}
        expected = {"harm_reduction_uniform_minus_hybrid": compact(harm, hci),
                    "useful_acceptance_hybrid_minus_uniform": {"difference": useful_diff, "ci95": useful_ci,
                                                              "paired_rows": useful["paired_rows"], "independent_tasks": useful["independent_tasks"]},
                    "harm_reduction_edit_minus_hybrid": compact(eharm, eci),
                    "complete_arm_pairing": complete, "missing_assigned_rows_per_required_comparison": missing,
                    "complete_required_assigned_observations": observed,
                    "harm_reduction_at_least_005_and_ci_excludes_zero": harm_ok,
                    "useful_noninferiority_ci_lower_above_minus_005": useful_ok,
                    "useful_all_zero_paired_differences": zero,
                    "useful_noninferiority_population_claim_supported": useful_ok and adequacy and not zero,
                    "minimum_40_harmful_and_40_useful_tasks": adequacy,
                    "recommendation_adequacy": adequacy and not zero,
                    "h2_holm4_below_005": p_ok, "static_edit_directional_benefit": edit_ok,
                    "static_edit_ci_excludes_zero": eci is not None and eci[0] > 0,
                    "numerical_policy_criteria_met": complete and harm_ok and useful_ok and p_ok and edit_ok,
                    "bounded_policy_criteria_met": complete and observed and harm_ok and useful_ok and p_ok and edit_ok and adequacy and not zero}
        checks.subset("model.gate." + reviewer, public_g.get(reviewer), expected)
    # Generated comparisons use the same paired counting, with intent strata.
    generated_groups = defaultdict(list)
    for r in rows:
        if r["cohort"] == "generated" and r["replicate"] == 0 and r["eligible"] is True:
            generated_groups[(r["split"], r["reviewer"], r["proposer"], r["intent"])].append(r)
    public_gen = index_public(report.get("generated_secondary_comparisons", []), lambda x: (x["split"], x["reviewer"], x["proposer"], x["intent"], x["left"], x["right"], x["layer"]))
    expected_gen = {}
    for group, subset in generated_groups.items():
        for a, b in (("selected_w", "uniform_w"), ("uniform_a", "hybrid"), ("edit", "hybrid")):
            for layer in LAYERS:
                expected_gen[group + (a, b, layer)] = paired_counts(subset, a, b, layer)
    checks.same("model.generated_comparison_coverage", sorted(map(repr, public_gen)), sorted(map(repr, expected_gen)))
    for key in public_gen.keys() & expected_gen.keys():
        e, a = expected_gen[key], public_gen[key]
        checks.subset("model.generated." + repr(key), a, {k: v for k, v in e.items() if k != "directions"})
        for d in DIRECTIONS:
            checks.subset("model.generated." + repr(key) + "." + d, a["directions"][d], e["directions"][d])


def offline_counts(rows):
    detected = sum(r["detected"] is True for r in rows)
    known = sum(r["detected"] is not None for r in rows)
    feasible = [r for r in rows if r["supplier_feasible"] is True]
    return {
        "assigned_rows": len(rows), "independent_tasks": len({r["task_id"] for r in rows}),
        "missing_rows": sum(r["_missing_row"] for r in rows),
        "unknown_detection_rows": len(rows) - known,
        "operational_detection_all_assigned": fraction(detected, len(rows)),
        "operational_miss_all_assigned": fraction(len(rows) - detected, len(rows)),
        "detection_known_only": fraction(detected, known),
        "supplier_feasibility": {"fully_feasible": len(feasible),
                                 "infeasible": sum(r["supplier_feasible"] is False for r in rows),
                                 "unknown": sum(r["supplier_feasible"] is None for r in rows)},
        "detection_supplier_fully_feasible_only": fraction(sum(r["detected"] is True for r in feasible), len(feasible)),
        "eligibility_reasons": dict(Counter(reason for r in rows for reason in r["eligibility_reasons"])),
        "logical_costs": {name: {"total_known": sum(r[name] for r in rows if r[name] is not None),
                                 "unknown_rows": sum(r[name] is None for r in rows)}
                          for name in ("logical_supplier_executions", "logical_independent_executions")},
    }


def offline_pairs(rows, left, right="hybrid"):
    """Integer sufficient statistics followed by equal-weight source-task means.

    This does not bootstrap, generate tests, or inspect program outcomes beyond
    supplied detected flags. An unobserved detection is an operational miss.
    """
    arms = {policy: {} for policy in (left, right)}
    for row in rows:
        if row["policy"] in arms:
            key = row_key(row, OFFLINE_ID[:-1])
            if key in arms[row["policy"]]:
                raise ValueError("Duplicate offline policy pair")
            arms[row["policy"]][key] = row
    akeys, bkeys = set(arms[left]), set(arms[right])
    common = akeys & bkeys
    by_task, known_task, seeds = defaultdict(list), defaultdict(list), defaultdict(set)
    missing = mismatched = unknown_cost = 0
    for key in common:
        a, b = arms[left][key], arms[right][key]
        delta = int(b["detected"] is True) - int(a["detected"] is True)
        by_task[a["task_id"]].append(delta)
        seeds[a["task_id"], a["proposal_id"]].add(a["replicate"])
        if a["detected"] is None or b["detected"] is None:
            missing += 1
        else:
            known_task[a["task_id"]].append(delta)
        cost_pairs = [(a[name], b[name]) for name in ("logical_supplier_executions", "logical_independent_executions")]
        if any(x is None or y is None for x, y in cost_pairs):
            unknown_cost += 1
        elif any(x != y for x, y in cost_pairs):
            mismatched += 1
    # Fractions avoid dependence on iteration order and make task weighting
    # explicit even when tasks have different numbers of proposals or seeds.
    means = [Fraction(sum(values), len(values)) for values in by_task.values()]
    known_means = [Fraction(sum(values), len(values)) for values in known_task.values()]
    difference = float(sum(means) / len(means)) if means else None
    proposals = {(r["task_id"], r["proposal_id"]) for arm in arms.values() for r in arm.values()}
    entirely_unpaired = len(proposals - set(seeds))
    missing_seeds = sum(len(SEEDS - actual) for actual in seeds.values())
    extra_seeds = sum(len(actual - SEEDS) for actual in seeds.values())
    violations = {policy: {
        "supplier_over_16_rows": sum(r["logical_supplier_executions"] is not None and r["logical_supplier_executions"] > 16 for r in arms[policy].values()),
        "independent_over_requested_rows": sum(r["logical_independent_executions"] is not None and r["logical_independent_executions"] > r["budget"] for r in arms[policy].values())}
        for policy in (left, right)}
    return {
        "left": left, "right": right, "difference": difference,
        "known_detection_only_difference": float(sum(known_means) / len(known_means)) if known_means else None,
        "known_detection_only_task_count": len(known_means),
        "paired_rows": len(common), "independent_tasks": len(means),
        "left_assigned": len(akeys), "right_assigned": len(bkeys),
        "left_only_unpaired": len(akeys - bkeys), "right_only_unpaired": len(bkeys - akeys),
        "expected_replicates": sorted(SEEDS), "missing_paired_replicates": missing_seeds,
        "extra_paired_replicates": extra_seeds, "entirely_unpaired_proposals": entirely_unpaired,
        "missing_detection_pairs": missing, "logical_cost_mismatch_pairs": mismatched,
        "logical_cost_unknown_pairs": unknown_cost,
        "complete_arm_and_replicate_pairing": bool(means) and not (akeys != bkeys or missing_seeds or extra_seeds or entirely_unpaired),
        "matched_logical_costs": bool(common) and mismatched == unknown_cost == 0,
        "requested_budget_violations": violations,
        "within_frozen_requested_budgets": not any(n for v in violations.values() for n in v.values()),
        "minimum_40_tasks": len(means) >= 40,
        "all_zero_task_differences": bool(means) and all(value == 0 for value in means),
        "bootstrap_degenerate": bool(means) and len(set(means)) == 1,
        "bootstrap_samples": 5000,
    }


def offline_gate(uniform, edit, primary, uniform_ci, edit_ci):
    """Arithmetic only: supplied CIs are not independently validated intervals."""
    enough = uniform["minimum_40_tasks"] and edit["minimum_40_tasks"]
    complete = uniform["complete_arm_and_replicate_pairing"] and edit["complete_arm_and_replicate_pairing"]
    observed = uniform["missing_detection_pairs"] == edit["missing_detection_pairs"] == 0
    costs = uniform["matched_logical_costs"] and edit["matched_logical_costs"]
    budget = uniform["within_frozen_requested_budgets"] and edit["within_frozen_requested_budgets"]
    effect = uniform["difference"] is not None and uniform["difference"] >= .05 and uniform_ci is not None and uniform_ci[0] > 0
    edit_effect = edit["difference"] is not None and edit["difference"] > 0
    return {"primary_stratum": primary, "minimum_40_tasks": enough,
            "complete_pairing_and_replicates": complete, "all_detections_observed": observed,
            "matched_logical_costs": costs, "within_frozen_requested_budgets": budget,
            "uniform_harm_margin_and_ci": effect, "static_edit_directional_benefit": edit_effect,
            "static_edit_ci_excludes_zero": edit_ci is not None and edit_ci[0] > 0,
            "bounded_offline_criteria_met": primary and enough and complete and observed and costs and budget and effect and edit_effect}


def offline_machine_difference(rows, left, right="hybrid"):
    """Reproduce the frozen sorted binary-float reduction, separately from truth.

    Integer task totals and rational means in offline_pairs remain authoritative
    for interpreting an exact zero. This second path checks the archived machine
    flag without misrepresenting roundoff as a scientific directional benefit.
    """
    arms = {policy: {} for policy in (left, right)}
    for row in rows:
        if row["policy"] in arms:
            key = row_key(row, OFFLINE_ID[:-1])
            if key in arms[row["policy"]]:
                raise ValueError("Duplicate offline policy pair")
            arms[row["policy"]][key] = row
    by_task = defaultdict(list)
    for key in arms[left].keys() & arms[right].keys():
        a, b = arms[left][key], arms[right][key]
        by_task[a["task_id"]].append(int(b["detected"] is True) - int(a["detected"] is True))
    means = [sum(values) / len(values) for _, values in sorted(by_task.items())]
    return sum(means) / len(means) if means else None


def audit_offline(rows, report, checks):
    checks.subset("offline.configuration", report.get("configuration"), {
        "expected_replicates": sorted(SEEDS), "bootstrap_samples": 5000,
        "seed": "praxis008-offline-analysis-v1", "primary_budget": 8, "secondary_budget": 4,
        "recommendation_minimum_tasks": 40})
    checks.subset("offline.accounting", report.get("accounting"), {
        "assignment_mode": "explicit_expected_assignment_inventory", "assigned_rows": len(rows),
        "independent_tasks": len({r["task_id"] for r in rows}),
        "eligible_rows": sum(r["eligible"] is True for r in rows),
        "ineligible_rows": sum(r["eligible"] is False for r in rows),
        "missing_rows_materialized": sum(r["_missing_row"] for r in rows),
        "unknown_detection_rows": sum(r["detected"] is None for r in rows)})
    grouped, strata = defaultdict(list), defaultdict(list)
    for row in rows:
        grouped[row_key(row, OFFLINE_GROUP)].append(row)
        if row["eligible"] is True:
            strata[row_key(row, OFFLINE_GROUP[:6])].append(row)
    public_counts = index_public(report["policy_counts"], lambda x: row_key(x["group"], OFFLINE_GROUP))
    checks.same("offline.count_group_coverage", sorted(map(repr, public_counts)), sorted(map(repr, grouped)))
    for key in grouped.keys() & public_counts.keys():
        checks.subset("offline.counts." + repr(key), public_counts[key], offline_counts(grouped[key]))
    public_pairs = index_public(report["comparisons"], lambda x: row_key(x["group"], OFFLINE_GROUP[:6]) + (x["left"], x["right"]))
    expected_pairs = {group + (policy, "hybrid"): offline_pairs(values, policy)
                      for group, values in strata.items() for policy in ("uniform", "edit", "fixed", "complement")}
    checks.same("offline.comparison_coverage", sorted(map(repr, public_pairs)), sorted(map(repr, expected_pairs)))
    cis = {}
    for key in public_pairs.keys() & expected_pairs.keys():
        expected, published = expected_pairs[key], public_pairs[key]
        primary = key[0] == "heldout" and key[1] == "native" and key[4] == "harmful" and key[5] == 8
        ci = check_ci(checks, "offline.comparison." + repr(key), published.get("ci95"), expected["independent_tasks"])
        cis[key] = ci
        expected.update(
            role="primary_offline_characterization" if primary else "secondary_descriptive",
            bootstrap_seed=json.dumps(("praxis008-offline-analysis-v1", key[:6]), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            harm_margin_005_and_ci_excludes_zero=expected["difference"] is not None and expected["difference"] >= .05 and ci is not None and ci[0] > 0)
        checks.subset("offline.comparison." + repr(key), published, expected)
    public_gates = index_public(report["recommendation_gates"], lambda x: row_key(x["group"], OFFLINE_GROUP[:6]))
    checks.same("offline.gate_coverage", sorted(map(repr, public_gates)), sorted(map(repr, strata)))
    for group in strata:
        ukey, ekey = group + ("uniform", "hybrid"), group + ("edit", "hybrid")
        primary = group[0] == "heldout" and group[1] == "native" and group[4] == "harmful" and group[5] == 8
        machine_pairs = {}
        for key, policy in ((ukey, "uniform"), (ekey, "edit")):
            machine = offline_machine_difference(strata[group], policy)
            actual = public_pairs.get(key, {}).get("difference")
            checks.condition("offline.machine_reduction." + repr(key),
                             type(actual) is type(machine) and actual == machine,
                             "Frozen sorted floating-point reduction differs: " + repr((actual, machine)))
            machine_pairs[key] = dict(expected_pairs[key], difference=machine)
        exact_gate = offline_gate(expected_pairs[ukey], expected_pairs[ekey], primary, cis.get(ukey), cis.get(ekey))
        gate = offline_gate(machine_pairs[ukey], machine_pairs[ekey], primary, cis.get(ukey), cis.get(ekey))
        if exact_gate != gate:
            changed = {field: {"exact_arithmetic": exact_gate[field], "archived_machine": gate[field]}
                       for field in gate if exact_gate[field] != gate[field]}
            warning = "NUMERICAL ERRATUM " + repr(group) + ": " + json.dumps(changed, sort_keys=True)
            warning += "; exact edit-minus-hybrid=" + repr(expected_pairs[ekey]["difference"])
            warning += ", frozen float=" + repr(machine_pairs[ekey]["difference"])
            warning += ". An exact zero is no directional benefit; preserve archived bytes and report the correction."
            checks.rows.append({"check": "offline.exact_arithmetic_erratum." + repr(group),
                                "passed": True, "detail": warning, "warning": warning})
        checks.subset("offline.gate." + repr(group), public_gates.get(group), gate)


def audit_statistics(decisions, expected, offline, offline_expected, model_report, acquisition_report):
    """Audit in-memory rows only after the parent releases the study archive.

    Explicit expected inventories are required. This helper neither reads files
    nor establishes provenance/authenticity. It independently implements counts,
    exact tests, and gate arithmetic but accepts published CIs as inputs. It is
    NOT authorship-independent of the frozen analysis. Separate reviewer controls
    and raw-record provenance checks must accompany its receipt.
    """
    checks = Checks()
    checks.rows.append({"check": "scope", "passed": True,
                        "detail": "Separate implementation by frozen-analysis author; counts/exact tests/gate arithmetic only; published CIs are inputs, no independent bootstrap or coverage verification; caller establishes archive release/provenance/authenticity."})
    for label, observed, inventory, report, audit, is_offline in (
        ("model", decisions, expected, model_report, audit_models, False),
        ("offline", offline, offline_expected, acquisition_report, audit_offline, True)):
        try:
            if inventory is None:
                raise ValueError("An explicit expected assignment inventory is required")
            rows = join_assignments(observed, inventory, is_offline)
            checks.condition(label + ".input_integrity", True, "")
            audit(rows, report, checks)
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as error:
            checks.condition(label + ".audit_completed", False, type(error).__name__ + ": " + str(error))
    return checks.rows
