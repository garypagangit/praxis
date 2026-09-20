"""Only artificial fixtures; no released SOC data or model downloads are read."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.cert_gate import exploratory_benchmark as benchmark
from experiments.cert_gate.calibration import calibrate
from experiments.cert_gate.feature_grouping import feature_group_sha
from experiments.cert_gate.scorers import LinearSVMScorer, serialize_features


def fixture_rows():
    rows = []
    for i in range(320):
        attack = i % 2 == 1
        rows.append({"rule_name": "fixture rule", "host": "fixture-host",
                     "uri": f"/fixture/{i}", "proto": "HTTP", "rsp_status": 200,
                     "req_body": ("unapproved exploit credential theft" if attack else "approved scheduled health check") + " client 192.0.2.1",
                     "Label": "Attack" if attack else "Non-Attack",
                     "attack_type": "derived annotation", "kill_chain_all": "derived annotation"})
    rows.append({**rows[70], "req_body": rows[70]["req_body"].replace("192.0.2.1", "198.51.100.2")})
    rows.append({**rows[0], "req_body": rows[0]["req_body"].replace("192.0.2.1", "198.51.100.3")})
    rows.append({**rows[80], "Label": "Attack"})
    return rows


def fixture_files(folder):
    rows = fixture_rows()
    source, audit, protocol = folder / "SOURCE.json", folder / "AUDIT.json", folder / "PROTOCOL.json"
    benchmark.write_json(source, rows)
    source_hash = benchmark.sha_bytes(source.read_bytes())
    cases = []
    for i in range(50):
        digest = benchmark.sha_bytes(benchmark.canonical({k: v for k, v in rows[i].items() if k != "Label"}))
        cases.append({"source_row_zero_based": i, "input_content_sha256": digest,
                      "case_id": benchmark.sha_bytes(f"{i}|{digest}".encode())})
    benchmark.write_json(audit, {"source_sha256": source_hash, "sample": cases, "human_review": {"cases": 50, "status": "PENDING"}})
    spec = {"release_status": benchmark.RELEASE, "seed": 20260920, "split_fractions": benchmark.FRACTIONS,
            "alpha": .01, "delta": .05, "bootstrap_repetitions": 10000,
            "expected_source_sha256": source_hash, "expected_audit_sha256": benchmark.sha_bytes(audit.read_bytes()),
            "scorer_config_sha256": LinearSVMScorer(seed=20260920).metadata()["config_sha256"],
            "grouping": benchmark.GROUPING}
    benchmark.write_json(protocol, spec)
    return rows, source, protocol, audit, source_hash


class ExploratoryBenchmarkTests(unittest.TestCase):
    def test_normalized_groups_hold_out_all_review_and_mixed_label_members(self):
        rows = fixture_rows()
        parts, manifest, summary = benchmark.build_splits(rows, range(50), 20260920)
        retained = {i for groups in parts.values() for g in groups for i in g["source_ordinals"]}
        self.assertTrue(set(range(50)).isdisjoint(retained))
        self.assertNotIn(321, retained)  # IPv4 variant of held case 0.
        self.assertNotIn(80, retained)
        self.assertNotIn(322, retained)  # Mixed label exact duplicate.
        group = next(g for g in manifest["retained_groups"] if 70 in g["source_ordinals"])
        self.assertEqual(group["source_ordinals"], [70, 320])
        self.assertEqual(group["representative_ordinal"], 70)
        self.assertEqual(len(group["exact_feature_sha256"]), 2)
        self.assertEqual(summary["exclusion_reason_counts"]["held_human_review"], {"groups": 50, "rows": 51})
        self.assertEqual(summary["exclusion_reason_counts"]["mixed_labels"], {"groups": 1, "rows": 2})
        sets = [{g["group_sha256"] for g in parts[role]} for role in benchmark.ROLES]
        for i, left in enumerate(sets):
            for right in sets[i + 1:]:
                self.assertTrue(left.isdisjoint(right))

    def test_split_hash_is_label_independent_and_does_not_change_model_text(self):
        row = fixture_rows()[70]
        other = {**row, "Label": "Attack", "attack_type": "changed derived tag", "kill_chain_all": "changed"}
        self.assertEqual(feature_group_sha(row), feature_group_sha(other))
        self.assertEqual(benchmark.split_role(feature_group_sha(row), 20260920), benchmark.split_role(feature_group_sha(other), 20260920))
        changed_ip = {**row, "req_body": row["req_body"].replace("192.0.2.1", "203.0.113.20")}
        self.assertEqual(feature_group_sha(row), feature_group_sha(changed_ip))
        self.assertNotEqual(serialize_features(row), serialize_features(changed_ip))
        for digest in ("0" * 64, "a" * 64, "f" * 64):
            h = int(hashlib.sha256(f"20260920|{digest}".encode()).hexdigest(), 16)
            expected = next((role for role, limit in (("fit", 40), ("selection", 50), ("calibration", 80)) if h * 100 < limit * 2 ** 256), "test")
            self.assertEqual(benchmark.split_role(digest, 20260920), expected)

    def test_marginal_formula_and_pac_use_different_sample_requirements(self):
        scores = np.arange(99, dtype=float)
        marginal = benchmark.marginal_calibrate(scores, .01)
        self.assertEqual(marginal["mode"], "MARGINAL_EXPECTATION_ONLY")
        self.assertEqual(marginal["threshold"]["value"], 98.0)
        self.assertEqual(marginal["expectation_bound_under_assumptions"], .01)
        self.assertEqual(benchmark.marginal_calibrate(scores[:98], .01)["mode"], "KEEP_ALL")
        pac = calibrate(scores)
        decisions = benchmark.predictions([98., 99.], pac, marginal)
        np.testing.assert_array_equal(decisions["PAC_SCORE_ONLY"], [False, False])
        np.testing.assert_array_equal(decisions["MARGINAL_CRC_FORMULA"], [False, True])
        self.assertEqual(benchmark.marginal_calibrate([.5] * 500, .01)["threshold"]["value"], .5)

    def test_zero_margin_ties_are_retained_and_metrics_have_declared_denominators(self):
        pac, marginal = calibrate([]), benchmark.marginal_calibrate([], .01)
        pred = benchmark.predictions([-1., 0., 1., 2.], pac, marginal)
        np.testing.assert_array_equal(pred["ZERO_MARGIN"], [False, False, True, True])
        labels = [1, 1, 0, 1]
        classifier = benchmark.classifier_metrics(labels, [-1., 0., 1., 2.])
        self.assertEqual((classifier["TP"], classifier["FP"], classifier["FN"], classifier["TN"]), (1, 0, 2, 1))
        metrics = benchmark.suppression_metrics(labels, pred["ZERO_MARGIN"])
        self.assertEqual(metrics["attack_suppression_fraction"], 1 / 3)
        self.assertEqual(metrics["nonattack_suppression_fraction"], 1.)

    def test_bootstrap_resamples_actual_group_counts_not_representative_copies(self):
        reps = {arm: np.zeros(2, dtype=bool) for arm in benchmark.ARMS}
        removed = {arm: np.zeros(2, dtype=int) for arm in benchmark.ARMS}
        removed["ZERO_MARGIN"] = np.array([0, 2])
        # The benign group's representative stays; two other members suppress.
        summary, draws = benchmark.bootstrap_rates([1, 0], reps, [1, 3], removed, 1000, 8)
        primary = draws["primary_unique_groups__ZERO_MARGIN__nonattack_suppression_fraction"]
        secondary = draws["secondary_all_rows__ZERO_MARGIN__nonattack_suppression_fraction"]
        self.assertTrue(np.all(primary[np.isfinite(primary)] == 0))
        np.testing.assert_allclose(secondary[np.isfinite(secondary)], 2 / 3)
        self.assertIn("not an incident/population confidence interval", summary["interpretation"])

    def test_protocol_source_and_audit_guards_precede_any_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, source, protocol, audit, source_hash = fixture_files(root)
            original = json.loads(protocol.read_bytes())
            for field, changed in (("release_status", "DRAFT"), ("expected_source_sha256", "0" * 64),
                                   ("expected_audit_sha256", "0" * 64), ("scorer_config_sha256", "0" * 64),
                                   ("seed", True), ("grouping", "unregistered")):
                with self.subTest(field=field):
                    value = copy.deepcopy(original)
                    value[field] = changed
                    benchmark.write_json(protocol, value)
                    with patch.object(benchmark, "EXPECTED_SOURCE_SHA256", source_hash):
                        with self.assertRaises(ValueError):
                            benchmark.run(source, protocol, audit, root / "private", root / "public")
                    self.assertFalse((root / "private").exists())
                    self.assertFalse((root / "public").exists())

    def test_tampered_review_binding_rejected_even_if_audit_hash_is_updated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, source, protocol, audit, source_hash = fixture_files(root)
            data = json.loads(audit.read_bytes())
            data["sample"][0]["source_row_zero_based"] = 51
            benchmark.write_json(audit, data)
            spec = json.loads(protocol.read_bytes())
            spec["expected_audit_sha256"] = benchmark.sha_bytes(audit.read_bytes())
            benchmark.write_json(protocol, spec)
            with patch.object(benchmark, "EXPECTED_SOURCE_SHA256", source_hash):
                with self.assertRaisesRegex(ValueError, "Review case does not bind"):
                    benchmark.validate_inputs(source, protocol, audit)

    def test_actual_svm_fixture_pipeline_freezes_before_test_and_preserves_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows, source, protocol, audit, source_hash = fixture_files(root)
            private, public = root / "private", root / "public"
            original_score = LinearSVMScorer.score
            observed_test_calls = []

            def guarded_score(scorer, alerts):
                for row in alerts:
                    role = benchmark.split_role(feature_group_sha(row), 20260920)
                    if role == "test":
                        freeze = json.loads((public / "CALIBRATION_FREEZE.json").read_bytes())
                        self.assertEqual(freeze["status"], "FROZEN_BEFORE_TEST_SCORING")
                        self.assertFalse(freeze["operational_certification"])
                        observed_test_calls.append(feature_group_sha(row))
                return original_score(scorer, alerts)

            with patch.object(benchmark, "EXPECTED_SOURCE_SHA256", source_hash), \
                 patch.object(benchmark, "committed_inputs", return_value={"git_commit": "SYNTHETIC_FIXTURE", "committed_file_sha256": {}}), \
                 patch.object(LinearSVMScorer, "score", guarded_score):
                result = benchmark.run(source, protocol, audit, private, public)
            self.assertTrue(observed_test_calls)
            self.assertFalse(result["operational_certification"])
            self.assertFalse(result["selection_used_for_tuning"])
            self.assertEqual(set(result["suppression"]["primary_unique_groups"]), set(benchmark.ARMS))
            self.assertGreater(result["memory"]["final_process_peak"]["bytes"], 0)
            manifest = json.loads((private / "SPLIT_MANIFEST.json").read_bytes())
            fit_indices = [g["representative_ordinal"] for g in manifest["retained_groups"] if g["role"] == "fit"]
            expected_fit_hash = benchmark.sha_bytes(benchmark.canonical({"features": [serialize_features(rows[i]) for i in fit_indices], "attack_labels": [benchmark.LABELS[rows[i]["Label"]] for i in fit_indices]}))
            self.assertEqual(result["scorer"]["fit_sha256"], expected_fit_hash)
            with np.load(private / "TEST_PREDICTIONS.npz", allow_pickle=False) as saved:
                self.assertTrue(set(saved["source_ordinals"].tolist()).isdisjoint(range(50)))
                for arm in benchmark.ARMS:
                    expected = benchmark.suppression_metrics(saved["labels"], saved[arm])
                    self.assertEqual(result["suppression"]["secondary_all_rows"][arm], expected)
            for name, record in result["private_artifacts"].items():
                self.assertEqual(benchmark.sha_bytes((private / name).read_bytes()), record["sha256"])
            public_text = (public / "RESULTS.json").read_text(encoding="utf-8")
            self.assertNotIn(str(private), public_text)
            self.assertNotIn("/fixture/", public_text)
            with self.assertRaisesRegex(ValueError, "must be new"):
                benchmark.run(source, protocol, audit, private, public)


if __name__ == "__main__":
    unittest.main()
