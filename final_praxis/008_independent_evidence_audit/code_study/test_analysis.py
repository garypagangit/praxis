"""Independent synthetic accounting/statistical controls; no study data loaded."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analysis import (accepted, analyze, exact_paired_p, holm_adjust,
                      outcome_direction, paired_comparison, prepare_rows,
                      render_markdown, summarize_arm)
import offline_analysis as offline


def record(task, arm, accept=False, direction="harmful", reviewer="model-a", **extra):
    outcomes = {"harmful": (True, False), "useful": (False, True),
                "other": (True, True), "unknown": (True, None)}
    y0, y1 = outcomes[direction]
    row = dict(task_id=str(task), split="heldout", cohort="native", direction=direction,
               reviewer=reviewer, proposer=None, proposal_id="native:" + direction,
               arm=arm, replicate=0, y0=y0, y1=y1,
               decision="accept" if accept else "keep", authenticated_failure=False,
               model_valid=True, proposal_status="valid", eligible=True,
               eligibility_reasons=[])
    row.update(extra)
    return row


def normalized(rows):
    return prepare_rows(rows)[0]


class AnalysisControls(unittest.TestCase):
    def test_reserved_labels_define_direction_and_require_literal_bool(self):
        self.assertEqual(outcome_direction(True, False), "harmful")
        self.assertEqual(outcome_direction(False, True), "useful")
        self.assertEqual(outcome_direction(False, False), "other")
        self.assertEqual(outcome_direction(None, False), "unknown")
        for change in ({"direction": "useful"}, {"y0": 1}, {"y1": "false"},
                       {"model_valid": "true"}, {"authenticated_failure": 0},
                       {"eligible": "true"}, {"eligibility_reasons": "reason"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_rows([{**record("x", "uniform_w"), **change}])
        rows = normalized([record("x", "uniform_w", direction="unknown")])
        self.assertEqual(rows[0]["direction"], "unknown")

    def test_authenticated_failure_vetoes_every_arm_but_not_reviewer_layer(self):
        for arm in ("no_witness", "uniform_w", "selected_w", "uniform_a", "edit", "hybrid"):
            row = record("x", arm, True, authenticated_failure=True)
            self.assertEqual(accepted(row, "reviewer_only"), 1)
            self.assertEqual(accepted(row, "enforced"), 0)
        self.assertEqual(accepted(record("x", "hybrid", True), "enforced"), 1)
        self.assertEqual(accepted(record("x", "hybrid", True, model_valid=False), "reviewer_only"), 0)

    def test_missing_call_materialized_and_retained_in_conditional_denominator(self):
        observed = [record("a", "hybrid", True)]
        assigned = observed + [record("b", "hybrid", True)]
        rows, mode = prepare_rows(observed, assigned)
        result = summarize_arm(rows)
        self.assertEqual(mode, "explicit_expected_assignment_inventory")
        self.assertEqual(result["assigned"], 2)
        self.assertEqual(result["missing_rows"], 1)
        self.assertEqual(result["valid_model_calls"], 1)
        harm = result["layers"]["enforced"]["by_direction"]["harmful"]
        self.assertEqual(harm["conditional_all_assigned"], {"numerator": 1, "denominator": 2, "rate": 0.5})
        self.assertEqual(harm["conditional_valid_calls_only"]["rate"], 1)
        self.assertEqual(result["layers"]["enforced"]["original_correct_preserved_among_known"]["rate"], 0.5)

    def test_unknown_outcome_is_not_a_measured_success_or_harm(self):
        rows = normalized([record("a", "hybrid", True), record("b", "hybrid", True, direction="unknown"),
                           record("c", "hybrid", False, direction="useful")])
        result = summarize_arm(rows)
        self.assertEqual(result["directions"], {"harmful": 1, "useful": 1, "other": 0, "unknown": 1})
        layer = result["layers"]["enforced"]
        self.assertEqual(layer["by_direction"]["harmful"]["conditional_all_assigned"]["denominator"], 1)
        self.assertEqual(layer["by_direction"]["harmful"]["unconditional_all_assignments"]["denominator"], 3)
        self.assertEqual(layer["final_reserved_suite_unknown"], 1)
        self.assertEqual(layer["final_reserved_suite_pass_among_known"]["denominator"], 2)

    def test_identity_and_reserved_label_conflicts_fail(self):
        source = record("x", "uniform_w")
        for rows in ([source, source],
                     [source, {**source, "arm": "selected_w", "y1": True, "direction": "other"}],
                     [source, {**source, "arm": "selected_w", "eligible": False}],
                     [source, {**source, "split": "dev", "arm": "selected_w"}]):
            with self.assertRaises(ValueError):
                prepare_rows(rows)
        with self.assertRaises(ValueError):
            prepare_rows([source], [record("different", "uniform_w")])
        with self.assertRaises(ValueError):
            prepare_rows([source], [source, source])

    def test_distinct_proposals_keep_their_identity_even_with_same_outcome(self):
        rows = normalized([record("x", "uniform_w", direction="other", cohort="generated", proposal_id="repair"),
                           record("x", "uniform_w", direction="other", cohort="generated", proposal_id="corruption")])
        self.assertEqual(len(rows), 2)

    def test_exact_paired_tail_and_holm_known_values(self):
        # Four favorable, zero unfavorable discordances: P[Bin(4, .5)>=4]=1/16.
        self.assertEqual(exact_paired_p(4, 0), 1 / 16)
        # P[Bin(4, .5)>=3]=(4+1)/16.
        self.assertEqual(exact_paired_p(3, 1), 5 / 16)
        self.assertEqual(exact_paired_p(0, 0), 1)
        self.assertEqual(exact_paired_p(0, 4), 1)
        # Sorted ranks are .01, .03, .04, .2; adjusted .04, .09, .09, .2.
        for actual, expected in zip(holm_adjust([0.03, 0.01, 0.2, 0.04]), [0.09, 0.04, 0.2, 0.09]):
            self.assertAlmostEqual(actual, expected)
        with self.assertRaises(ValueError):
            exact_paired_p(1.5, 2)
        with self.assertRaises(ValueError):
            holm_adjust([float("nan")])

    def test_paired_cells_and_directional_sign_are_hand_specified(self):
        pairs = [(True, False), (True, False), (False, True), (True, True), (False, False)]
        rows = normalized([record(task, arm, decision) for task, pair in enumerate(pairs)
                           for arm, decision in zip(("selected_w", "uniform_w"), pair)])
        result = paired_comparison(rows, "selected_w", "uniform_w", "reviewer_only", 100)
        harm = result["directions"]["harmful"]
        self.assertEqual(harm["paired_cells"], {"both_accept": 1, "left_only_accept": 2,
                                               "right_only_accept": 1, "neither_accept": 1})
        self.assertEqual(harm["difference"], 0.2)
        self.assertEqual(harm["one_sided_exact_p"], 0.5)
        self.assertEqual(result["independent_task_clusters"], 5)

    def test_task_cluster_bootstrap_preserves_multiple_directions_and_repeats(self):
        rows = []
        # Two source tasks. Their harmful/useful contrast vectors are identical,
        # so joint task resampling must yield identical CIs across directions.
        for task, diff in (("a", True), ("b", False)):
            for direction in ("harmful", "useful"):
                for arm, decision in (("uniform_a", diff), ("hybrid", not diff)):
                    rows.append(record(task, arm, decision, direction=direction))
        base = normalized(rows)
        result = paired_comparison(base, "uniform_a", "hybrid", "enforced", 400, "synthetic")
        self.assertEqual(result["independent_task_clusters"], 2)
        self.assertEqual(result["directions"]["harmful"]["ci95"], result["directions"]["useful"]["ci95"])
        repeated = base + normalized([{**row, "replicate": 1} for row in rows])
        repeat_result = paired_comparison(repeated, "uniform_a", "hybrid", "enforced", 400, "synthetic")
        self.assertEqual(repeat_result["independent_task_clusters"], 2)
        self.assertEqual(repeat_result["directions"]["harmful"]["ci95"], result["directions"]["harmful"]["ci95"])
        self.assertFalse(repeat_result["directions"]["harmful"]["exact_sign_eligible"])
        self.assertIsNone(repeat_result["directions"]["harmful"]["one_sided_exact_p"])
        self.assertEqual(result, paired_comparison(base[::-1], "uniform_a", "hybrid", "enforced", 400, "synthetic"))

    def test_duplicate_model_or_proposal_observations_cannot_inflate_exact_test(self):
        rows = normalized([record("same-task", arm, arm == "uniform_a", reviewer=model)
                           for model in ("model-a", "model-b") for arm in ("uniform_a", "hybrid")])
        result = paired_comparison(rows, "uniform_a", "hybrid", "enforced", 20)
        self.assertEqual(result["directions"]["harmful"]["paired_rows"], 2)
        self.assertEqual(result["directions"]["harmful"]["independent_tasks"], 1)
        self.assertIsNone(result["directions"]["harmful"]["one_sided_exact_p"])

    def test_primary_family_has_four_even_when_models_or_arms_absent(self):
        rows = [record("a", "selected_w", True), record("a", "uniform_w", False)]
        result = analyze(rows, ("model-a", "model-b"), bootstrap_samples=20)
        self.assertEqual(len(result["primary_hypotheses"]), 4)
        self.assertEqual(sum(item["analysis_eligible"] for item in result["primary_hypotheses"]), 1)
        self.assertEqual(result["primary_hypotheses"][0]["raw_one_sided_exact_p"], 0.5)
        self.assertTrue(all(item["holm4_adjusted_p"] == 1 for item in result["primary_hypotheses"]))
        self.assertFalse(any(item["bounded_policy_criteria_met"] for item in result["policy_gates"]))

    def test_development_repeats_and_undeclared_eligibility_cannot_enter_primary(self):
        rows = [record("held", "selected_w", True), record("held", "uniform_w", False)]
        additions = [record("dev", arm, arm == "uniform_w", split="dev") for arm in ("selected_w", "uniform_w")]
        additions += [{**row, "replicate": 1, "decision": "keep" if row["decision"] == "accept" else "accept"} for row in rows]
        additions += [record("excluded", arm, arm == "uniform_w", eligible=False, eligibility_reasons=["incompatible"])
                      for arm in ("selected_w", "uniform_w")]
        additions += [record("undeclared", arm, arm == "uniform_w", eligible=None) for arm in ("selected_w", "uniform_w")]
        first = analyze(rows, ("model-a", "model-b"), bootstrap_samples=20)
        second = analyze(rows + additions, ("model-a", "model-b"), bootstrap_samples=20)
        self.assertEqual(first["primary_hypotheses"], second["primary_hypotheses"])
        self.assertEqual(second["accounting"]["assigned_rows"], 10)
        self.assertEqual(second["accounting"]["ineligible_rows"], 2)
        self.assertEqual(second["accounting"]["eligibility_undeclared_rows"], 2)
        self.assertEqual(second["stability"]["groups"][0]["layers"]["reviewer_only"]["acceptance_agreement"]["rate"], 0)

    def test_missing_arm_cannot_silently_become_complete_case_primary(self):
        rows = [record("a", "selected_w", True), record("a", "uniform_w", False), record("b", "selected_w", True)]
        result = analyze(rows, ("model-a", "model-b"), bootstrap_samples=20)
        self.assertFalse(result["primary_hypotheses"][0]["analysis_eligible"])
        self.assertEqual(result["primary_hypotheses"][0]["family_p"], 1)
        assigned = rows + [record("b", "uniform_w")]
        full = analyze(rows, ("model-a", "model-b"), assigned, bootstrap_samples=20)
        self.assertTrue(full["primary_hypotheses"][0]["analysis_eligible"])
        self.assertEqual(full["primary_hypotheses"][0]["paired_rows"], 2)
        self.assertEqual(full["accounting"]["missing_rows_materialized"], 1)

    def test_policy_gate_rejects_uniform_improvement_that_overblocks_useful_edits(self):
        def fixture(keep_useful):
            rows = []
            for model in ("model-a", "model-b"):
                for task in range(40):
                    for direction in ("harmful", "useful"):
                        for arm in ("uniform_a", "edit", "hybrid"):
                            accept = arm != "hybrid" or (direction == "useful" and keep_useful)
                            rows.append(record(task, arm, accept, reviewer=model, direction=direction))
            return rows
        bad = analyze(fixture(False), ("model-a", "model-b"), bootstrap_samples=20)
        self.assertTrue(all(row["harm_reduction_at_least_005_and_ci_excludes_zero"] for row in bad["policy_gates"]))
        self.assertTrue(all(not row["useful_noninferiority_ci_lower_above_minus_005"] for row in bad["policy_gates"]))
        self.assertTrue(all(not row["bounded_policy_criteria_met"] for row in bad["policy_gates"]))
        good = analyze(fixture(True), ("model-a", "model-b"), bootstrap_samples=20)
        self.assertTrue(all(row["numerical_policy_criteria_met"] for row in good["policy_gates"]))
        self.assertTrue(all(row["useful_all_zero_paired_differences"] for row in good["policy_gates"]))
        self.assertTrue(all(not row["bounded_policy_criteria_met"] for row in good["policy_gates"]))
        self.assertEqual(good["policy_gates"][0]["useful_acceptance_hybrid_minus_uniform"]["difference"], 0)
        mixed = fixture(True)
        for row in mixed:
            if row["task_id"] == "0" and row["direction"] == "useful" and row["arm"] == "uniform_a":
                row["decision"] = "keep"
        mixed_result = analyze(mixed, ("model-a", "model-b"), bootstrap_samples=20)
        self.assertTrue(all(row["bounded_policy_criteria_met"] for row in mixed_result["policy_gates"]))
        small = analyze([row for row in mixed if int(row["task_id"]) < 8], ("model-a", "model-b"), bootstrap_samples=20)
        self.assertTrue(all(not row["minimum_40_harmful_and_40_useful_tasks"] for row in small["policy_gates"]))

    def test_generated_intent_is_separate_and_never_called_natural_error(self):
        rows = [record("a", arm, arm == "selected_w", cohort="generated", proposer="proposer-a",
                       intent=intent, proposal_id=intent)
                for intent in ("honest_repair", "adversarial_corruption")
                for arm in ("selected_w", "uniform_w", "uniform_a", "edit", "hybrid")]
        result = analyze(rows, ("model-a", "model-b"), bootstrap_samples=20)
        self.assertTrue(all(not row["analysis_eligible"] for row in result["primary_hypotheses"]))
        comps = result["generated_secondary_comparisons"]
        self.assertEqual({row["intent"] for row in comps}, {"honest_repair", "adversarial_corruption"})
        self.assertTrue(all("not naturally occurring model error" in row["interpretation"] for row in comps))
        self.assertTrue(any(row["left"] == "edit" for row in comps))

    def test_empty_report_is_json_safe_and_readable_without_invented_rates(self):
        result = analyze([], ("model-a", "model-b"), bootstrap_samples=20)
        json.dumps(result, allow_nan=False)
        self.assertIsNone(result["primary_hypotheses"][0]["difference"])
        text = render_markdown(result)
        self.assertIn("undefined", text)
        self.assertIn("0; independent source tasks: 0", text)
        self.assertIn("not a novelty certificate", text)

    def test_cli_protocol_hash_checked_before_model_file_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            protocol = path / "frozen.md"
            protocol.write_text("synthetic protocol", encoding="utf-8")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("analysis.py")),
                                     str(path / "NONEXISTENT_MODEL_OUTPUTS.jsonl"), "--reviewer", "model-a",
                                     "--reviewer", "model-b", "--frozen-protocol", str(protocol),
                                     "--expected-protocol-sha256", "0" * 64,
                                     "--output-json", str(path / "out.json"),
                                     "--output-markdown", str(path / "out.md")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Frozen protocol hash mismatch", result.stderr)
            self.assertNotIn("FileNotFoundError", result.stderr)
            self.assertFalse((path / "out.json").exists())


def policy_record(task, policy, detected=False, **extra):
    row = dict(task_id=str(task), split="heldout", cohort="native", proposal_id="native:harmful",
               direction="harmful", policy=policy, replicate=0, budget=8, detected=detected,
               eligible=True, logical_supplier_executions=16, logical_independent_executions=8)
    row.update(extra)
    return row


class OfflineAnalysisControls(unittest.TestCase):
    def test_twenty_repeats_are_one_task_and_contrast_sign_is_correct(self):
        rows = [policy_record("same", policy, policy == "hybrid", replicate=replicate)
                for replicate in range(20) for policy in ("uniform", "hybrid")]
        prepared, _ = offline.prepare_rows(rows)
        result = offline.compare(prepared, "uniform", bootstrap_samples=100)
        self.assertEqual(result["difference"], 1)
        self.assertEqual(result["paired_rows"], 20)
        self.assertEqual(result["independent_tasks"], 1)
        self.assertEqual(result["ci95"], [1, 1])
        self.assertTrue(result["complete_arm_and_replicate_pairing"])
        self.assertFalse(result["minimum_40_tasks"])
        self.assertNotIn("one_sided_exact_p", result)

    def test_task_weight_is_equal_despite_unequal_proposal_counts(self):
        rows = [policy_record("a", policy, policy == "hybrid", proposal_id="a:" + str(proposal))
                for proposal in range(5) for policy in ("uniform", "hybrid")]
        rows += [policy_record("b", policy, policy == "uniform") for policy in ("uniform", "hybrid")]
        prepared, _ = offline.prepare_rows(rows)
        result = offline.compare(prepared, "uniform", expected_replicates=(0,), bootstrap_samples=100)
        self.assertEqual(result["paired_rows"], 6)
        self.assertEqual(result["independent_tasks"], 2)
        self.assertEqual(result["difference"], 0)
        self.assertEqual(result["ci95"], [-1, 1])
        self.assertEqual(result, offline.compare(prepared[::-1], "uniform", expected_replicates=(0,), bootstrap_samples=100))

    def test_missing_replicates_and_unequal_costs_block_recommendation(self):
        rows = [policy_record(task, policy, policy == "hybrid")
                for task in range(40) for policy in ("uniform", "edit", "hybrid")]
        result = offline.analyze(rows, bootstrap_samples=20)
        gate = result["recommendation_gates"][0]
        self.assertTrue(gate["minimum_40_tasks"])
        self.assertFalse(gate["complete_pairing_and_replicates"])
        self.assertFalse(gate["bounded_offline_criteria_met"])
        result = offline.analyze(rows, expected_replicates=(0,), bootstrap_samples=20)
        self.assertTrue(result["recommendation_gates"][0]["bounded_offline_criteria_met"])
        for row in rows:
            if row["policy"] == "hybrid":
                row["logical_independent_executions"] = 16
        result = offline.analyze(rows, expected_replicates=(0,), bootstrap_samples=20)
        self.assertFalse(result["recommendation_gates"][0]["matched_logical_costs"])
        self.assertFalse(result["recommendation_gates"][0]["bounded_offline_criteria_met"])

    def test_unknown_execution_is_operational_miss_and_explicitly_unknown(self):
        assigned = [policy_record("a", "uniform", True), policy_record("a", "hybrid", True)]
        rows, mode = offline.prepare_rows(assigned[:1], assigned)
        self.assertEqual(mode, "explicit_expected_assignment_inventory")
        summary = offline.summarize(rows)
        self.assertEqual(summary["assigned_rows"], 2)
        self.assertEqual(summary["missing_rows"], 1)
        self.assertEqual(summary["operational_miss_all_assigned"]["rate"], 0.5)
        self.assertEqual(summary["detection_known_only"]["rate"], 1)
        result = offline.compare(rows, "uniform", expected_replicates=(0,), bootstrap_samples=20)
        self.assertEqual(result["difference"], -1)
        self.assertIsNone(result["known_detection_only_difference"])
        self.assertEqual(result["missing_detection_pairs"], 1)
        self.assertEqual(result["logical_cost_unknown_pairs"], 1)

    def test_offline_identity_labels_and_mixed_strata_fail_closed(self):
        row = policy_record("a", "uniform")
        with self.assertRaises(ValueError):
            offline.prepare_rows([row, row])
        with self.assertRaises(ValueError):
            offline.prepare_rows([row, {**row, "policy": "hybrid", "direction": "useful"}])
        with self.assertRaises(ValueError):
            offline.prepare_rows([row, {**row, "policy": "hybrid", "eligible": False}])
        with self.assertRaises(ValueError):
            offline.prepare_rows([row, {**row, "policy": "hybrid", "split": "dev"}])
        for field, value in (("detected", 1), ("eligible", "true"), ("logical_supplier_executions", -1)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                offline.prepare_rows([{**row, field: value}])
        mixed, _ = offline.prepare_rows([row, policy_record("b", "uniform", budget=4)])
        with self.assertRaises(ValueError):
            offline.compare(mixed, "uniform", bootstrap_samples=20)

    def test_budget4_development_and_ineligible_rows_remain_descriptive(self):
        rows = [policy_record(task, policy, policy == "hybrid", budget=budget,
                              split=split, eligible=eligible)
                for task, budget, split, eligible in (("base", 8, "heldout", True), ("short", 4, "heldout", True),
                                                      ("dev", 8, "dev", True), ("excluded", 8, "heldout", False))
                for policy in ("uniform", "edit", "hybrid")]
        result = offline.analyze(rows, expected_replicates=(0,), bootstrap_samples=20)
        self.assertEqual(result["accounting"]["assigned_rows"], 12)
        self.assertEqual(result["accounting"]["ineligible_rows"], 3)
        self.assertEqual(sum(row["primary_stratum"] for row in result["recommendation_gates"]), 1)
        self.assertEqual(sum(row["role"] == "primary_offline_characterization" for row in result["comparisons"]), 4)

    def test_empty_offline_report_is_readable_and_json_finite(self):
        result = offline.analyze([], bootstrap_samples=20)
        self.assertEqual(result["comparisons"], [])
        self.assertEqual(result["accounting"]["assigned_rows"], 0)
        json.dumps(result, allow_nan=False)
        self.assertIn("independent source tasks: 0", offline.render_markdown(result))


if __name__ == "__main__":
    unittest.main()
