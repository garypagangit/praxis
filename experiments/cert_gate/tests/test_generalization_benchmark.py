"""Artificial fixtures only for the fixed harder-generalization comparison."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.cert_gate import generalization_benchmark as benchmark
from experiments.cert_gate.evidence_checker import evidence_view, evidence_group_sha, has_evidence
from experiments.cert_gate.scorers import LinearSVMScorer, serialize_features
from experiments.cert_gate.tests.test_exploratory_benchmark import fixture_rows


def make_fixture(folder):
    rows = fixture_rows()
    for i in range(320):
        rows[i]["rule_name"] = f"synthetic-rule-{i // 4}"
    for target, original in ((320, 70), (321, 0), (322, 80)):
        rows[target]["rule_name"] = rows[original]["rule_name"]
    rows.append({**rows[70], "rule_name": "synthetic-other-rule", "host": "different-host"})
    for i in range(6):
        rows.append({"rule_name": f"empty-rule-{i}", "host": f"empty-host-{i}", "proto": "HTTP", "method": "GET", "Label": "Non-Attack"})
    source, audit, protocol = folder / "SOURCE.json", folder / "AUDIT.json", folder / "PROTOCOL.json"
    benchmark.prior.write_json(source, rows)
    source_hash = benchmark.prior.sha_bytes(source.read_bytes())
    sample = []
    for i in range(50):
        content = benchmark.prior.sha_bytes(benchmark.prior.canonical({k: v for k, v in rows[i].items() if k != "Label"}))
        sample.append({"source_row_zero_based": i, "input_content_sha256": content,
                       "case_id": benchmark.prior.sha_bytes(f"{i}|{content}".encode())})
    benchmark.prior.write_json(audit, {"source_sha256": source_hash, "sample": sample, "human_review": {"cases": 50, "status": "PENDING"}})
    spec = {"release_status": benchmark.RELEASE, "seed": 20260920, "split_fractions": benchmark.prior.FRACTIONS,
            "alpha": .01, "delta": .05, "bootstrap_repetitions": 10000, "grouping": benchmark.FAMILY_GROUPING,
            "regimes": list(benchmark.REGIMES), "conditions": list(benchmark.CONDITIONS), "arms": list(benchmark.ARMS),
            "practical_gate": benchmark.GATE, "expected_source_sha256": source_hash,
            "expected_audit_sha256": benchmark.prior.sha_bytes(audit.read_bytes()),
            "scorer_config_sha256": LinearSVMScorer(seed=20260920).metadata()["config_sha256"]}
    benchmark.prior.write_json(protocol, spec)
    return rows, source, protocol, audit, source_hash


class GeneralizationBenchmarkTests(unittest.TestCase):
    def test_both_view_duplicate_families_and_empty_evidence_do_not_leak(self):
        with tempfile.TemporaryDirectory() as temp:
            rows, *_ = make_fixture(Path(temp))
            for regime in benchmark.REGIMES:
                parts, manifest, summary = benchmark.build_family_splits(rows, range(50), 20260920, regime)
                kept = manifest["retained_groups"]
                family = next(g for g in kept if 70 in g["source_ordinals"])
                self.assertEqual(family["source_ordinals"], [70, 320, 323])
                self.assertEqual(family["representative_ordinal"], 70)
                self.assertEqual(len(family["full_view_group_sha256"]), 2)
                held_family = next(g for g in manifest["excluded_groups"] if 0 in g["source_ordinals"])
                self.assertIn(321, held_family["source_ordinals"])
                self.assertTrue({80, 322}.isdisjoint({i for g in kept for i in g["source_ordinals"]}))
                empty = [g for g in kept if g["representative_ordinal"] >= 324]
                self.assertEqual(len(empty), 6)  # Missing views never create one giant family.
                self.assertEqual(summary["no_meaningful_evidence_rows"], 6)
                evidence_roles = {}
                rule_roles = {}
                for role, groups in parts.items():
                    for g in groups:
                        for i in g["source_ordinals"]:
                            if has_evidence(rows[i]):
                                key = evidence_group_sha(rows[i])
                                evidence_roles.setdefault(key, set()).add(role)
                            rule_roles.setdefault(rows[i]["rule_name"], set()).add(role)
                self.assertTrue(all(len(roles) == 1 for roles in evidence_roles.values()))
                if regime == "rule_components":
                    self.assertTrue(all(len(roles) == 1 for roles in rule_roles.values()))

    def test_matching_threshold_handles_zero_all_interior_and_strict_ties(self):
        scores, labels = np.array([0., 1., 1., 2., -3.]), np.array([0, 0, 0, 0, 1])
        for mask, kind, target, achieved in (
            ([False] * 5, "positive_infinity", 0, 0),
            ([True, True, True, True, False], "negative_infinity", 4, 4),
            ([False, False, True, True, False], "finite", 2, 1),
            ([False, True, True, True, False], "finite", 3, 3),
        ):
            with self.subTest(target=target):
                result = benchmark.matched_utility_threshold(scores, labels, mask)
                self.assertEqual(result["threshold"]["kind"], kind)
                self.assertEqual(result["target_nonattack_suppressed"], target)
                self.assertEqual(result["achieved_nonattack_suppressed"], achieved)
                self.assertEqual(int(sum(benchmark.above(scores, result["threshold"]) & (labels == 0))), achieved)

    def test_component_bootstrap_preserves_mixed_class_component_and_row_weights(self):
        # First component has one attack and one benign representative; second
        # has one benign representative. It must not be split into class units.
        units = {"primary_representatives": {"labels": np.array([1, 0, 0]), "component_index": np.array([0, 0, 1]),
                                             "predictions": {"ARM": np.array([True, False, True])}},
                 "secondary_all_rows": {"labels": np.array([1, 1, 0, 0]), "component_index": np.array([0, 0, 0, 1]),
                                         "predictions": {"ARM": np.array([True, True, False, True])}}}
        summary, draws = benchmark.component_bootstrap(units, ["ARM"], 100, 42)
        rng = np.random.default_rng(42)
        for b in range(100):
            sample = rng.integers(0, 2, size=2)
            for unit, values in units.items():
                ix = np.concatenate([np.flatnonzero(values["component_index"] == component) for component in sample])
                y, s = values["labels"][ix], values["predictions"]["ARM"][ix]
                for label, metric in ((1, "attack_suppression_fraction"), (0, "nonattack_suppression_fraction")):
                    expected = np.nan if not sum(y == label) else np.sum(s & (y == label)) / np.sum(y == label)
                    actual = draws[f"{unit}__ARM__{metric}"][b]
                    self.assertTrue((np.isnan(expected) and np.isnan(actual)) or expected == actual)
        self.assertGreater(summary["bands"]["primary_representatives__ARM__attack_suppression_fraction"]["undefined_resamples"], 0)

    def decision_fixture(self, gate_attack=.005, gate_benign=.8):
        metrics = {"CROSS_VIEW_GATE_PAC": {"attack_suppression_fraction": gate_attack, "nonattack_suppression_fraction": gate_benign},
                   "FULL_PAC_SCORE_ONLY": {"attack_suppression_fraction": .03, "nonattack_suppression_fraction": .82},
                   "EVIDENCE_PAC_SCORE_ONLY": {"attack_suppression_fraction": .02, "nonattack_suppression_fraction": .83}}
        paired = {arm: {"attack_suppression_fraction": {"paired_percentiles_2_5_and_97_5": [-.04, -.001]},
                        "nonattack_suppression_fraction": {"paired_percentiles_2_5_and_97_5": [-.05, .02]}}
                  for arm in benchmark.GATE["comparators"]}
        return {"suppression": {"primary_representatives": metrics}, "paired_gate_comparisons": {"primary_representatives": paired}}

    def test_practical_gate_requires_same_route_against_both_and_strict_paired_band(self):
        data = self.decision_fixture()
        self.assertTrue(benchmark.practical_decision(data)["passed"])
        changed = copy.deepcopy(data)
        changed["paired_gate_comparisons"]["primary_representatives"]["EVIDENCE_PAC_SCORE_ONLY"]["attack_suppression_fraction"]["paired_percentiles_2_5_and_97_5"][1] = 0.
        self.assertFalse(benchmark.practical_decision(changed)["passed"])
        mixed = self.decision_fixture()
        mixed["suppression"]["primary_representatives"]["EVIDENCE_PAC_SCORE_ONLY"] = {"attack_suppression_fraction": .005, "nonattack_suppression_fraction": .70}
        mixed["paired_gate_comparisons"]["primary_representatives"]["EVIDENCE_PAC_SCORE_ONLY"]["nonattack_suppression_fraction"]["paired_percentiles_2_5_and_97_5"] = [.06, .13]
        result = benchmark.practical_decision(mixed)
        self.assertTrue(result["route_comparisons"]["A_attack_improvement"]["FULL_PAC_SCORE_ONLY"])
        self.assertTrue(result["route_comparisons"]["B_utility_improvement"]["EVIDENCE_PAC_SCORE_ONLY"])
        self.assertFalse(result["passed"])
        self.assertFalse(benchmark.practical_decision(self.decision_fixture(gate_attack=.011))["passed"])
        utility = self.decision_fixture()
        for arm in benchmark.GATE["comparators"]:
            utility["suppression"]["primary_representatives"][arm] = {"attack_suppression_fraction": .01, "nonattack_suppression_fraction": .70}
            utility["paired_gate_comparisons"]["primary_representatives"][arm]["nonattack_suppression_fraction"]["paired_percentiles_2_5_and_97_5"] = [.06, .13]
        self.assertTrue(benchmark.practical_decision(utility)["passed"])

    def test_protocol_and_source_guards_run_before_output_or_fit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            _, source, protocol, audit, source_hash = make_fixture(folder)
            original = json.loads(protocol.read_bytes())
            for field, value in (("release_status", "DRAFT"), ("expected_source_sha256", "0" * 64),
                                 ("arms", ["KEEP_ALL"]), ("seed", True), ("practical_gate", {})):
                spec = copy.deepcopy(original)
                spec[field] = value
                benchmark.prior.write_json(protocol, spec)
                with patch.object(benchmark.prior, "EXPECTED_SOURCE_SHA256", source_hash), patch.object(LinearSVMScorer, "fit") as fit:
                    with self.assertRaises(ValueError):
                        benchmark.run(source, protocol, audit, folder / "private", folder / "public")
                    fit.assert_not_called()
                self.assertFalse((folder / "private").exists())
                self.assertFalse((folder / "public").exists())

    def test_two_regime_synthetic_pipeline_global_freeze_private_predictions_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            rows, source, protocol, audit, source_hash = make_fixture(folder)
            private, public = folder / "private", folder / "public"
            layouts = {regime: benchmark.build_family_splits(rows, range(50), 20260920, regime)[0] for regime in benchmark.REGIMES}
            fingerprint_regime = {}
            for regime, parts in layouts.items():
                indices = [g["representative_ordinal"] for g in parts["fit"]]
                for view in ("full", "evidence"):
                    documents = [serialize_features(rows[i] if view == "full" else evidence_view(rows[i])) for i in indices]
                    fingerprint = benchmark.prior.sha_bytes(benchmark.prior.canonical({"features": documents, "attack_labels": [benchmark.prior.LABELS[rows[i]["Label"]] for i in indices]}))
                    fingerprint_regime[fingerprint] = regime
            original_score = LinearSVMScorer.score
            test_calls = []

            def guarded_score(model, alerts):
                regime = fingerprint_regime[model.metadata()["fit_sha256"]]
                test_ordinals = {i for g in layouts[regime]["test"] for i in g["source_ordinals"]}
                for alert in alerts:
                    uri = alert.get("uri", "")
                    if uri.startswith("/fixture/") and int(uri.rsplit("/", 1)[1]) in test_ordinals:
                        frozen = json.loads((public / "GLOBAL_CALIBRATION_FREEZE.json").read_bytes())
                        self.assertEqual(set(frozen["regimes"]), set(benchmark.REGIMES))
                        test_calls.append(regime)
                return original_score(model, alerts)

            with patch.object(benchmark.prior, "EXPECTED_SOURCE_SHA256", source_hash), \
                 patch.object(benchmark, "committed_inputs", return_value={"git_commit": "SYNTHETIC_FIXTURE", "committed_file_sha256": {}}), \
                 patch.object(LinearSVMScorer, "score", guarded_score):
                result = benchmark.run(source, protocol, audit, private, public)
            self.assertEqual(set(test_calls), set(benchmark.REGIMES))
            self.assertFalse(result["operational_certification"])
            frozen = json.loads((public / "GLOBAL_CALIBRATION_FREEZE.json").read_bytes())
            for regime in benchmark.REGIMES:
                cal = np.load(private / regime / "SCORES_calibration.npz", allow_pickle=False)
                n_attack = int(sum(cal["labels"] == 1))
                for name in ("full_pac", "evidence_pac", "gate_pac"):
                    self.assertEqual(frozen["regimes"][regime][name]["n_attack"], n_attack)
                self.assertEqual(frozen["regimes"][regime]["gate_pac"]["n_eligible_attack"], int(sum(cal["checker_eligible"] & (cal["labels"] == 1))))
                cal.close()
                for condition in benchmark.CONDITIONS:
                    prediction = np.load(private / regime / condition / "PREDICTIONS.npz", allow_pickle=False)
                    self.assertEqual(set(benchmark.ARMS) - set(prediction.files), set())
                    self.assertTrue(set(prediction["source_ordinals"].tolist()).isdisjoint(range(50)))
                    outcome = result["regimes"][regime]["conditions"][condition]
                    for arm in benchmark.ARMS:
                        self.assertEqual(outcome["suppression"]["secondary_all_rows"][arm], benchmark.prior.suppression_metrics(prediction["labels"], prediction[arm]))
                    prediction.close()
                key = "primary_representatives__CROSS_VIEW_GATE_PAC__attack_suppression_fraction"
                with np.load(private / regime / "directive" / "BOOTSTRAP_DRAWS.npz", allow_pickle=False) as changed, \
                     np.load(private / regime / "neutral" / "BOOTSTRAP_DRAWS.npz", allow_pickle=False) as reference:
                    differences = changed[key] - reference[key]
                    expected = np.quantile(differences[np.isfinite(differences)], [.025, .975]).tolist()
                report = result["regimes"][regime]["paired_condition_changes"]["directive_minus_neutral"]["effects"][key]
                self.assertEqual(report["paired_percentiles_2_5_and_97_5"], expected)
            for name, record in result["private_artifacts"].items():
                self.assertEqual(benchmark.prior.sha_bytes((private / name).read_bytes()), record["sha256"])
            self.assertNotIn(str(private), (public / "RESULTS.json").read_text())
            with self.assertRaisesRegex(ValueError, "must be new"):
                benchmark.run(source, protocol, audit, private, public)


if __name__ == "__main__":
    unittest.main()
