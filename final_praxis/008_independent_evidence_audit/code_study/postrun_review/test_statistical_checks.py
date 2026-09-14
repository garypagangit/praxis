"""Hand-specified synthetic controls; no frozen analysis or study data imports."""
import copy
import unittest

import statistical_checks as s


def model_row(task="t", arm="uniform_a", decision="accept", **changes):
    row = dict(task_id=task, split="heldout", cohort="native", reviewer=s.REVIEWERS[0],
               proposer=None, intent=None, proposal_id="harm", replicate=0, arm=arm,
               y0=True, y1=False, direction="harmful", eligible=True, eligibility_reasons=[],
               supplier_feasible=True, _missing_row=False, model_valid=True,
               authenticated_failure=False, decision=decision, proposal_status="qualified")
    row.update(changes)
    return row


def offline_row(task="t", policy="uniform", detected=False, **changes):
    row = dict(task_id=task, split="heldout", cohort="native", proposer=None, intent=None,
               proposal_id="harm", direction="harmful", policy=policy, replicate=0, budget=8,
               eligible=True, eligibility_reasons=[], supplier_feasible=True, _missing_row=False,
               detected=detected, logical_supplier_executions=16, logical_independent_executions=8)
    row.update(changes)
    return row


def empty_reports():
    """Literal empty-inventory expectations, including unchanged Holm family."""
    zero_rate = {"numerator": 0, "denominator": 0, "rate": None}
    direction = {"paired_rows": 0, "independent_tasks": 0,
                 "left_acceptance": zero_rate, "right_acceptance": zero_rate,
                 "difference": None, "ci95": None,
                 "paired_cells": {"both_accept": 0, "left_only_accept": 0, "right_only_accept": 0, "neither_accept": 0},
                 "exact_sign_eligible": False, "one_sided_exact_p": None}
    comparisons, hypotheses, gates = [], [], []
    for reviewer in s.REVIEWERS:
        for left, right in (("selected_w", "uniform_w"), ("uniform_a", "hybrid"), ("edit", "hybrid")):
            for layer in ("reviewer_only", "enforced"):
                comparisons.append(dict(reviewer=reviewer, left=left, right=right, layer=layer,
                    split="heldout", cohort="native", replicate=0, eligible=True,
                    left_assigned=0, right_assigned=0, left_only_unpaired=0, right_only_unpaired=0,
                    left_missing_assigned_rows=0, right_missing_assigned_rows=0, paired_missing_assigned_rows=0,
                    paired_rows=0, independent_task_clusters=0,
                    directions={d: copy.deepcopy(direction) for d in ("harmful", "useful", "other", "unknown")}))
        for h, layer, contrast in (("H1", "reviewer_only", "selected_w minus uniform_w"), ("H2", "enforced", "uniform_a minus hybrid")):
            hypotheses.append(dict(hypothesis=h, reviewer=reviewer, layer=layer, contrast=contrast,
                direction="harmful", analysis_eligible=False, difference=None, ci95=None,
                paired_rows=0, independent_tasks=0, raw_one_sided_exact_p=None, family_p=1.0,
                holm4_adjusted_p=1.0, reject_at_005=False))
        compact = dict(difference=None, ci95=None, paired_rows=0, independent_tasks=0)
        gates.append(dict(reviewer=reviewer,
            harm_reduction_uniform_minus_hybrid=compact,
            useful_acceptance_hybrid_minus_uniform=compact,
            harm_reduction_edit_minus_hybrid=compact,
            complete_arm_pairing=True,
            missing_assigned_rows_per_required_comparison={"uniform_hybrid": 0, "edit_hybrid": 0, "selected_uniform_witness": 0},
            complete_required_assigned_observations=True,
            harm_reduction_at_least_005_and_ci_excludes_zero=False,
            useful_noninferiority_ci_lower_above_minus_005=False,
            useful_all_zero_paired_differences=False,
            useful_noninferiority_population_claim_supported=False,
            minimum_40_harmful_and_40_useful_tasks=False, recommendation_adequacy=False,
            h2_holm4_below_005=False, static_edit_directional_benefit=False,
            static_edit_ci_excludes_zero=False, numerical_policy_criteria_met=False, bounded_policy_criteria_met=False))
    model = dict(
        configuration=dict(reviewers=list(s.REVIEWERS), primary_split="heldout", primary_replicate=0,
            bootstrap_samples=5000, seed="praxis008-analysis-v1", holm_family_size=4,
            harm_margin=.05, useful_noninferiority_margin=-.05, recommendation_minimum_tasks_per_direction=40),
        accounting=dict(assignment_mode="explicit_expected_assignment_inventory", assigned_rows=0,
            independent_source_tasks=0, missing_rows_materialized=0, replicate_rows_secondary_only=0,
            unknown_reserved_outcome_rows=0, eligible_rows=0, ineligible_rows=0,
            eligibility_undeclared_rows=0, generated_intent_missing_rows=0),
        arm_summaries=[], native_primary_comparisons=comparisons, primary_hypotheses=hypotheses,
        policy_gates=gates, generated_secondary_comparisons=[])
    offline = dict(
        configuration=dict(expected_replicates=list(range(20)), bootstrap_samples=5000,
            seed="praxis008-offline-analysis-v1", primary_budget=8, secondary_budget=4, recommendation_minimum_tasks=40),
        accounting=dict(assignment_mode="explicit_expected_assignment_inventory", assigned_rows=0,
            independent_tasks=0, eligible_rows=0, ineligible_rows=0, missing_rows_materialized=0, unknown_detection_rows=0),
        policy_counts=[], comparisons=[], recommendation_gates=[])
    return model, offline


class StatisticalChecks(unittest.TestCase):
    def test_exact_zero_and_frozen_float_are_separate(self):
        # (1/10 + 2/10 - 3/10) / 3 is exactly zero, but ordinary sorted
        # binary floating summation is positive. This is a machine artifact.
        rows = []
        for task, delta in (("a", 1), ("b", 2), ("c", -3)):
            for seed in range(10):
                rows.append(offline_row(task, "edit", delta < 0 and seed < -delta, replicate=seed))
                rows.append(offline_row(task, "hybrid", delta > 0 and seed < delta, replicate=seed))
        self.assertEqual(s.offline_pairs(rows, "edit")["difference"], 0.0)
        self.assertEqual(s.offline_machine_difference(rows, "edit"), (0.1 + 0.2 - 0.3) / 3)
        self.assertGreater(s.offline_machine_difference(rows, "edit"), 0)
        self.assertEqual(s.offline_machine_difference(list(reversed(rows)), "edit"), s.offline_machine_difference(rows, "edit"))

    def test_machine_difference_empty_and_duplicate_fail_closed(self):
        self.assertIsNone(s.offline_machine_difference([], "edit"))
        row = offline_row("a", "edit")
        with self.assertRaises(ValueError):
            s.offline_machine_difference([row, row], "edit")

    def test_exact_tail_manual_eight_discordances(self):
        # P[X>=6]=(28+8+1)/256, and empty discordance has p=1.
        self.assertEqual(s.binomial_tail(6, 2), 37 / 256)
        self.assertEqual(s.binomial_tail(0, 0), 1)
        self.assertEqual(s.binomial_tail(8, 0), 1 / 256)

    def test_holm_manual_unsorted(self):
        self.assertEqual(s.holm_four([.04, .01, .03, .20]), [.09, .04, .09, .20])
        with self.assertRaises(ValueError):
            s.holm_four([.01, .02])
        with self.assertRaises(ValueError):
            s.binomial_tail(True, 2)

    def test_layer_and_invalid_output_semantics(self):
        row = model_row(authenticated_failure=True)
        self.assertEqual(s.accept(row, "reviewer_only"), 1)
        self.assertEqual(s.accept(row, "enforced"), 0)
        self.assertEqual(s.accept(model_row(model_valid=False), "reviewer_only"), 0)
        with self.assertRaises(ValueError):
            s.accept(row, "undeclared_layer")

    def test_paired_cells_independently_enumerated(self):
        decisions = [("accept", "accept"), ("accept", "keep"), ("keep", "accept"), ("keep", "keep"), ("accept", "keep")]
        rows = [model_row(str(i), arm, dec) for i, pair in enumerate(decisions)
                for arm, dec in zip(("uniform_a", "hybrid"), pair)]
        result = s.paired_counts(rows, "uniform_a", "hybrid", "enforced")["directions"]["harmful"]
        self.assertEqual(result["paired_cells"], dict(both_accept=1, left_only_accept=2, right_only_accept=1, neither_accept=1))
        self.assertEqual(result["difference"], .2)
        self.assertEqual(result["one_sided_exact_p"], .5)
        self.assertEqual(result["left_acceptance"], dict(numerator=3, denominator=5, rate=.6))

    def test_repeated_proposals_not_independent_sign_trials(self):
        rows = [model_row("same", arm, "accept" if arm == "uniform_a" else "keep", proposal_id=proposal)
                for proposal in ("a", "b") for arm in ("uniform_a", "hybrid")]
        result = s.paired_counts(rows, "uniform_a", "hybrid", "enforced")["directions"]["harmful"]
        self.assertEqual((result["paired_rows"], result["independent_tasks"]), (2, 1))
        self.assertFalse(result["exact_sign_eligible"])
        self.assertIsNone(result["one_sided_exact_p"])

    def test_arm_denominators_and_unknown_final(self):
        rows = [model_row("a"), model_row("b", model_valid=False),
                model_row("c", decision="keep", y0=None, y1=True, direction="unknown")]
        result = s.arm_counts(rows)
        layer = result["layers"]["enforced"]
        harm = layer["by_direction"]["harmful"]
        self.assertEqual(harm["conditional_all_assigned"], dict(numerator=1, denominator=2, rate=.5))
        self.assertEqual(harm["conditional_valid_calls_only"], dict(numerator=1, denominator=1, rate=1.0))
        self.assertEqual(harm["unconditional_all_assignments"]["denominator"], 3)
        self.assertEqual(layer["final_reserved_suite_pass_among_known"], dict(numerator=1, denominator=2, rate=.5))
        self.assertEqual(layer["final_reserved_suite_unknown"], 1)

    def test_missing_expected_is_retained(self):
        expected = [model_row(arm=arm) for arm in ("uniform_a", "hybrid")]
        rows = s.join_assignments(expected[:1], expected)
        result = s.paired_counts(rows, "uniform_a", "hybrid", "enforced")
        self.assertEqual(result["right_missing_assigned_rows"], 1)
        self.assertEqual(result["paired_rows"], 1)
        self.assertEqual(result["directions"]["harmful"]["difference"], 1.0)

    def test_unknown_assignment_labels_can_be_filled(self):
        observed = model_row()
        expected = dict(observed, y0=None, y1=None, direction="unknown")
        self.assertEqual(s.join_assignments([observed], [expected])[0]["direction"], "harmful")

    def test_integrity_rejects_duplicate_unexpected_crosssplit(self):
        row = model_row()
        with self.assertRaises(ValueError):
            s.join_assignments([row, row], [row])
        with self.assertRaises(ValueError):
            s.join_assignments([row], [])
        dev = model_row(split="dev", proposal_id="other")
        with self.assertRaises(ValueError):
            s.join_assignments([row, dev], [row, dev])

    def test_task_average_not_seed_or_proposal_weighted(self):
        rows = []
        # Task A has three proposals, all +1; task B one proposal, all -1.
        # Equal task mean=0, pooled row mean would be +.5.
        for task, proposals in (("A", range(3)), ("B", range(1))):
            for proposal in proposals:
                for seed in range(20):
                    rows.extend([offline_row(task, "uniform", task == "B", proposal_id=str(proposal), replicate=seed),
                                 offline_row(task, "hybrid", task == "A", proposal_id=str(proposal), replicate=seed)])
        result = s.offline_pairs(rows, "uniform")
        self.assertEqual(result["difference"], 0)
        self.assertEqual((result["paired_rows"], result["independent_tasks"]), (80, 2))
        self.assertTrue(result["complete_arm_and_replicate_pairing"])
        self.assertFalse(result["minimum_40_tasks"])

    def test_missing_unknown_and_known_only_are_distinct(self):
        expected = [offline_row("A", policy, policy == "hybrid", replicate=seed)
                    for seed in range(20) for policy in ("uniform", "hybrid")]
        observed = [r for r in expected if not (r["policy"] == "hybrid" and r["replicate"] == 0)]
        rows = s.join_assignments(observed, expected, True)
        result = s.offline_pairs(rows, "uniform")
        self.assertEqual(result["difference"], 19 / 20)
        self.assertEqual(result["known_detection_only_difference"], 1.0)
        self.assertEqual(result["missing_detection_pairs"], 1)
        self.assertEqual(result["logical_cost_unknown_pairs"], 1)
        self.assertTrue(result["complete_arm_and_replicate_pairing"])
        self.assertFalse(result["matched_logical_costs"])

    def test_unpaired_missing_extra_seed_completeness(self):
        rows = [offline_row("a", policy, replicate=seed)
                for seed in (0, 20) for policy in ("uniform", "hybrid")]
        rows.append(offline_row("b", "uniform"))
        result = s.offline_pairs(rows, "uniform")
        self.assertEqual(result["missing_paired_replicates"], 19)
        self.assertEqual(result["extra_paired_replicates"], 1)
        self.assertEqual(result["entirely_unpaired_proposals"], 1)
        self.assertFalse(result["complete_arm_and_replicate_pairing"])

    def test_overbudget_equal_costs_block_gate(self):
        rows = [offline_row(str(task), policy, policy == "hybrid", replicate=seed)
                for task in range(40) for seed in range(20) for policy in ("uniform", "edit", "hybrid")]
        uniform, edit = s.offline_pairs(rows, "uniform"), s.offline_pairs(rows, "edit")
        self.assertTrue(s.offline_gate(uniform, edit, True, [1, 1], [1, 1])["bounded_offline_criteria_met"])
        for row in rows:
            row["logical_independent_executions"] = 9
        uniform, edit = s.offline_pairs(rows, "uniform"), s.offline_pairs(rows, "edit")
        self.assertTrue(uniform["matched_logical_costs"])
        self.assertEqual(uniform["requested_budget_violations"]["uniform"]["independent_over_requested_rows"], 800)
        self.assertFalse(s.offline_gate(uniform, edit, True, [1, 1], [1, 1])["bounded_offline_criteria_met"])

    def test_supplier_overbudget_and_secondary_cannot_recommend(self):
        rows = [offline_row("a", policy, policy == "hybrid", logical_supplier_executions=17)
                for policy in ("uniform", "hybrid")]
        result = s.offline_pairs(rows, "uniform")
        self.assertFalse(result["within_frozen_requested_budgets"])
        self.assertFalse(s.offline_gate(result, result, False, [1, 1], [1, 1])["bounded_offline_criteria_met"])

    def test_empty_report_end_to_end_manual_fixture(self):
        model, offline = empty_reports()
        checks = s.audit_statistics([], [], [], [], model, offline)
        self.assertTrue(all(c["passed"] for c in checks), [c for c in checks if not c["passed"]])
        self.assertGreater(len(checks), 500)

    def test_primary_family_tampering_and_ci_shape_are_caught(self):
        model, offline = empty_reports()
        model["primary_hypotheses"][0]["holm4_adjusted_p"] = .01
        model["native_primary_comparisons"][0]["directions"]["harmful"]["ci95"] = [0, 0]
        checks = s.audit_statistics([], [], [], [], model, offline)
        failed = [c["check"] for c in checks if not c["passed"]]
        self.assertTrue(any(name.endswith("holm4_adjusted_p") for name in failed))
        self.assertTrue(any(name.endswith("published_ci_shape_only") for name in failed))

    def test_dev_and_repeats_do_not_enter_primary_family(self):
        model, offline = empty_reports()
        # Deliberately partial report omits descriptive arm counts; only the
        # complete primary family assertions are tested by this control.
        rows = [model_row("dev", arm, split="dev") for arm in ("selected_w", "uniform_w")]
        rows += [model_row("repeat", arm, replicate=1) for arm in ("uniform_a", "hybrid")]
        checks = s.audit_statistics(rows, rows, [], [], model, offline)
        primary = [c for c in checks if c["check"].startswith("model.primary.")]
        self.assertTrue(primary)
        self.assertTrue(all(c["passed"] for c in primary), [c for c in primary if not c["passed"]])

    def test_report_coverage_missing_inventory_and_bool_count(self):
        model, offline = empty_reports()
        model["native_primary_comparisons"].pop()
        model["accounting"]["assigned_rows"] = False
        checks = s.audit_statistics([], [], [], None, model, offline)
        names = {c["check"] for c in checks if not c["passed"]}
        self.assertIn("model.native_comparison_coverage", names)
        self.assertIn("model.accounting.assigned_rows", names)
        self.assertIn("offline.audit_completed", names)


if __name__ == "__main__":
    unittest.main()
