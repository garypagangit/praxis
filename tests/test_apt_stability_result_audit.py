"""Independent audit qualification, including deliberately invalid evidence."""
from __future__ import annotations

import contextlib
import copy
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from experiments.apt_final.normal_stability.analysis import verify_results as audit


def configuration():
    path = Path(audit.__file__).parents[1] / "config.json"
    return audit.read(path)


def family():
    config = configuration()
    config.update(datasets=["tiny"], folds=[config["folds"][0]], encoder_seeds=[11, 19], bank_seeds=[71])
    records = []
    for d, f, e, b, s, a, c in itertools.product(config["datasets"], ["A"], [11, 19], [71], config["strategies"], audit.ARMS, config["conditions"]):
        records.append({"dataset": d, "fold": f, "encoder_seed": e, "bank_seed": b, "strategy": s,
                        "representation": a, "condition": c, "duplicate_of_encoder_seed": 11 if a == "local_knn" and e == 19 else None,
                        "metrics": {"false_positive_rate": .02, "recall": .5, "f1": .6 if s != "clean" else .4}})
    return config, records


class AuditContracts(unittest.TestCase):
    def test_exact_record_grid_rejects_missing_repeated_and_unregistered_cases(self):
        config, records = family()
        self.assertEqual(len(audit.check_records(records, config)), 36)
        for broken in (records[:-1], records + [records[0]], [*records[:-1], {**records[-1], "bank_seed": 999}]):
            with self.assertRaises(audit.AuditFailure):
                audit.check_records(broken, config)

    def test_duplicate_declarations_and_duplicate_metrics_are_checked(self):
        config, records = family()
        original = next(i for i, r in enumerate(records) if r["duplicate_of_encoder_seed"] is not None)
        bad = copy.deepcopy(records)
        bad[original]["duplicate_of_encoder_seed"] = None
        with self.assertRaisesRegex(audit.AuditFailure, "duplicate declaration"):
            audit.check_records(bad, config)
        bad = copy.deepcopy(records)
        bad[original]["metrics"]["f1"] = .9
        with self.assertRaisesRegex(audit.AuditFailure, "duplicate metrics"):
            audit.check_records(bad, config)

    def test_reference_budget_source_ids_and_disjoint_views_are_checked(self):
        fold = {"fit": ["train0", "train1"], "calibration": "train2", "validation": "train3"}
        sizes = {"train0": 7, "train1": 11, "train2": 100, "train3": 100, "test0": 500}
        selected = np.sort(np.random.default_rng(3011).choice(18, 12, replace=False))
        selection = {"train0": selected[selected < 7], "train1": selected[selected >= 7] - 7}
        mask = np.zeros(12, dtype=bool)
        mask[np.random.default_rng(np.random.SeedSequence([3011, 0x56494557])).permutation(12)[6:]] = True
        state = {"bank_row_graph": np.r_[np.zeros(len(selection["train0"]), dtype=np.int64), np.ones(len(selection["train1"]), dtype=np.int64)],
                 "bank_row_id": np.r_[selection["train0"], selection["train1"]], "pooled_is_masked": mask}
        meta = {"graph_names": ["train0", "train1"], "bank_rows": 12, "clean_rows": 6, "masked_rows": 6,
                "bank_seed": 3011, "allocation_domain": 0x56494557, "reference_multiplicity_preserved": True}
        self.assertEqual(audit.check_reference_rows(selection, state, meta, sizes, fold, 3011, 12), 12)
        for bad_selection, bad_state in (({**selection, "test0": np.array([0])}, state),
                                        ({**selection, "train0": np.array([0, 0])}, state),
                                        (selection, {**state, "pooled_is_masked": ~mask}),
                                        (selection, {**state, "bank_row_id": state["bank_row_id"] + 1})):
            with self.assertRaises(audit.AuditFailure):
                audit.check_reference_rows(bad_selection, bad_state, meta, sizes, fold, 3011, 12)

    def test_empirical_calibration_preserves_ties_and_exact_boundary_decisions(self):
        calibration = np.arange(99, dtype=np.float64)
        margin, p, prediction = audit.empirical_tail(calibration, np.array([98., 99., 100.]), .01)
        np.testing.assert_array_equal(p, [.02, .01, .01])
        np.testing.assert_array_equal(prediction, [False, True, True])
        np.testing.assert_array_equal(margin >= 0, prediction)
        _, tied, _ = audit.empirical_tail(np.ones(1000), np.array([1., 2.]), .01)
        np.testing.assert_array_equal(tied, [1., 1 / 1001])
        for cal, query in ((np.array([]), np.array([1.])), (np.array([np.nan]), np.array([1.])),
                           (np.array([1.]), np.array([np.inf])), (np.ones((2, 2)), np.array([1.]))):
            with self.assertRaises(audit.AuditFailure):
                audit.empirical_tail(cal, query, .01)

    def test_direct_distance_check_retains_reference_multiplicity_and_detects_bad_score(self):
        raw = np.array([[0., 0.], [0., 0.], [2., 0.], [2., 0.], [1., 2.]])
        query = np.array([[0., 0.], [1., 0.], [3., 3.]])
        mean, scale = raw.mean(0), np.maximum(raw.std(0), .001)
        distances = np.sqrt(np.sum((((raw[None, :, :] - mean) / scale) - ((query[:, None, :] - mean) / scale)) ** 2, axis=2))
        scores = np.sort(distances, axis=1)[:, :2].mean(1)
        self.assertEqual(scores[0], 0.)
        report = audit.check_unique_distances(raw, mean, scale, query, scores, 2)
        self.assertTrue(report["all_queries_reexecuted"])
        scores[0] += .1
        with self.assertRaisesRegex(audit.AuditFailure, "distance differs"):
            audit.check_unique_distances(raw, mean, scale, query, scores, 2)

    def test_node_type_false_alert_counts_are_independent(self):
        result = audit.normal_metrics(np.array([0, 1, 1, 0, 1], dtype=bool), np.array([0, 0, 1, 1, 2]))
        self.assertEqual(result["alerts"], 3)
        self.assertEqual(result["false_positive_rate"], .6)
        self.assertEqual(result["by_node_type"]["0"], {"n": 2, "alerts": 1, "false_positive_rate": .5})
        self.assertEqual(result["by_node_type"]["2"], {"n": 1, "alerts": 1, "false_positive_rate": 1.})

    def test_one_failed_repeat_blocks_gate_and_strongest_comparator_blocks_repair(self):
        config, records = family()
        baseline = {"records": {"tiny": {"original_best_fixed_mean_clean_f1": .1}}}
        result = audit.independent_decision(records, records, config, baseline)
        self.assertTrue(result["datasets"]["tiny"]["candidates"]["pooled_calibration/gin_knn"]["positive_repair"])
        bad_normal = copy.deepcopy(records)
        case = next(r for r in bad_normal if r["strategy"] == "pooled_calibration" and r["representation"] == "gin_knn")
        case["metrics"]["false_positive_rate"] = .0201
        result = audit.independent_decision(bad_normal, records, config, baseline)
        self.assertFalse(result["datasets"]["tiny"]["candidates"]["pooled_calibration/gin_knn"]["ready"])
        stronger = copy.deepcopy(records)
        for row in stronger:
            if row["strategy"] == "clean" and row["representation"] == "gin_knn" and row["condition"] == "masked":
                row["metrics"]["f1"] = .8
        result = audit.independent_decision(records, stronger, config, baseline)
        self.assertFalse(result["datasets"]["tiny"]["candidates"]["pooled_calibration/mlp_knn"]["positive_repair"])

    def test_paired_local_vs_neural_deltas_use_all_encoder_positions(self):
        config, records = family()
        for record in records:
            if record["representation"] == "local_knn":
                record["metrics"]["f1"] = .6
            elif record["representation"] == "gin_knn":
                record["metrics"]["f1"] = .1 if record["encoder_seed"] == 11 else .9
        answer = next(r for r in audit.paired_deltas(records, config)
                      if r["strategy"] == "pooled_calibration" and r["representation"] == "local_knn"
                      and r["condition"] == "masked" and r["clean_strategy_comparator"] == "gin_knn")
        self.assertEqual(answer["paired_cases"], 2)
        self.assertEqual(answer["local_duplicate_pair_positions"], 1)
        self.assertAlmostEqual(answer["mean_f1_delta"], .1)


class SourceBindingNegatives(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.here = self.root / "experiments" / "apt_final" / "normal_stability"
        self.native = self.here.parent / "native_graph"
        self.embedding = self.here.parent / "embedding_baseline"
        self.data = self.root / "data"
        for directory in (self.here, self.native, self.embedding, self.data):
            directory.mkdir(parents=True)
        self.config = self.here / "config.json"
        self.config.write_text('{"scope":"DEVELOPMENT_ONLY"}', encoding="utf-8")
        sources = [self.config]
        for directory, names in ((self.here, ("PROTOCOL.md", "PROTOCOL_REVIEW.md", "PINNED_BASELINES.json", "runner.py", "run_cloud.sh")),
                                 (self.native, ("data.py", "pilot.py", "provenance.py", "cloud_control.py")),
                                 (self.embedding, ("engine.py", "scoring.py"))):
            for name in names:
                path = directory / name
                path.write_text("synthetic binding test " + name, encoding="utf-8")
                sources.append(path)
        graph = self.data / "train0.npz"
        np.savez(graph, node_type=np.array([0], dtype=np.int64))
        manifest = {"status": "STATIC_DEVELOPMENT_ONLY", "adapter_sha256": audit.digest(self.native / "data.py"),
                    "datasets": [{"status": "STATIC_DEVELOPMENT_ONLY", "matches_upstream_git_blob": True,
                                  "graphs": [{"npz": graph.name, "npz_sha256": audit.digest(graph)}]}]}
        (self.data / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.registration = self.here / "REGISTRATION.json"
        self.reg = {"status": "FROZEN_NORMAL_STABILITY", "scope": "DEVELOPMENT_ONLY", "confirmation_registered": False,
                    "test_outcomes_previously_inspected": True, "predecessor_weights_used": False, "git_commit": "a" * 40,
                    "config_sha256": audit.digest(self.config), "data_manifest_sha256": audit.digest(self.data / "MANIFEST.json"),
                    "code_hashes": {p.relative_to(self.root).as_posix(): audit.digest(p) for p in sources},
                    "data_files": {graph.name: audit.digest(graph)}}
        self.registration.write_text(json.dumps(self.reg), encoding="utf-8")

    def bind(self, committed=None):
        def show(args, **_kwargs):
            relative = args[2].split(":", 1)[1]
            return (self.root / relative).read_bytes() if committed is None else committed
        with mock.patch.object(audit, "REPO", self.root), mock.patch.object(audit.subprocess, "check_output", side_effect=show):
            return audit.source_binding(self.config, self.data, self.registration)

    def test_matching_source_config_and_graph_inventory_bind(self):
        _, reg, _ = self.bind()
        self.assertEqual(reg["git_commit"], "a" * 40)

    def test_config_code_and_data_byte_changes_are_rejected(self):
        for path in (self.config, self.here / "runner.py", self.data / "train0.npz"):
            before = path.read_bytes()
            try:
                path.write_bytes(before + b" ")
                with self.subTest(path=path), self.assertRaises(audit.AuditFailure):
                    self.bind()
            finally:
                path.write_bytes(before)

    def test_working_bytes_must_match_the_registered_commit(self):
        with self.assertRaisesRegex(audit.AuditFailure, "committed snapshot"):
            self.bind(committed=b"wrong committed bytes")


class SyntheticAuditIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experiments.apt_final.normal_stability import runner
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.data = cls.root / "data"
        cls.data.mkdir()
        cls.output = cls.root / "output"
        cls.config = configuration()
        cls.config.update(datasets=["cadets"], encoder_seeds=[11, 19], bank_seeds=[71], hidden_dim=8,
                          bottleneck_dim=3, epochs=1, max_loss_nodes=8, cpu_threads=1,
                          embedding_batch_size=3, bank_size=12, neighbors=2, query_chunk_size=4)
        cls.config_path, cls.registration_path = cls.root / "config.json", cls.root / "REGISTRATION.json"
        cls.config_path.write_text(json.dumps(cls.config), encoding="utf-8")
        cls.registration_path.write_text('{"synthetic_only":true}', encoding="utf-8")
        (cls.root / "PINNED_BASELINES.json").write_text(json.dumps({"records": {"cadets": {"original_best_fixed_mean_clean_f1": .1}}}), encoding="utf-8")
        graphs = []
        for i, name in enumerate(["train0", "train1", "train2", "train3", "test0"]):
            path = cls.data / (name + ".npz")
            np.savez_compressed(path, node_type=np.asarray([(j + i) % 3 for j in range(8)], dtype=np.int64),
                                src=np.asarray([0, 1, 2, 3, 4, 5, i % 3]), dst=np.asarray([1, 2, 3, 4, 5, 6, 7]),
                                relation=np.asarray([(j + i) % 2 for j in range(7)]),
                                y=np.asarray([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int8) if name == "test0" else np.asarray([{"do_not_read": name}], dtype=object))
            graphs.append({"npz": path.name, "npz_sha256": audit.digest(path)})
        cls.manifest = {"datasets": [{"dataset": "cadets", "metadata": {"node_feature_dim": 3, "edge_feature_dim": 2}, "graphs": graphs}]}
        (cls.data / "MANIFEST.json").write_text(json.dumps(cls.manifest), encoding="utf-8")
        with mock.patch.object(runner, "verify_registration", return_value={"git_commit": "synthetic-only"}), contextlib.redirect_stdout(io.StringIO()):
            cls.result = runner.run(cls.config_path, cls.data, cls.output, cls.registration_path, "cpu")
        cls.registration = {"git_commit": cls.result["source_commit"], "config_sha256": cls.result["config_sha256"],
                            "data_manifest_sha256": cls.result["data_manifest_sha256"]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_audit(self):
        with mock.patch.object(audit, "source_binding", return_value=(self.config, self.registration, self.manifest)), contextlib.redirect_stdout(io.StringIO()):
            return audit.audit(self.config_path, self.data, self.output, self.registration_path)

    def test_all_actual_synthetic_artifacts_metrics_and_distance_queries_pass(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["logged_records_per_phase"], 144)
        self.assertEqual(result["unique_records_per_phase"], 120)
        self.assertEqual(result["distance_check_batches"], 288)
        self.assertTrue(result["distance_sampling"]["full_distance_reexecution"])
        self.assertFalse(result["neural_inference_rerun"])

    def test_any_modified_normal_score_artifact_is_rejected(self):
        target = next((self.output / "private").rglob("NORMAL_SCORES.npz"))
        original = target.read_bytes()
        try:
            target.write_bytes(original + b"changed")
            with self.assertRaisesRegex(audit.AuditFailure, "artifact inventory/hash differs"):
                self.run_audit()
        finally:
            target.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
