"""Meaningful software qualification; generated fixtures are never APT evidence."""
import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from experiments.apt_final import engine


def fixture():
    rows, edges = [], []
    for si, split in enumerate(("train", "gate_train", "calibration", "development", "confirmation")):
        for group_number in range(2):
            group = f"{split}-{group_number}"
            for j in range(12):
                rows.append({"id": f"{group}-{j}", "group_id": group, "split": split,
                             "time": si * 1000 + group_number * 100 + j,
                             "host_id": group, "features": [float(j % 2), j / 12],
                             "label": j % 2, "synthetic": True})
            # Two staggered layers allow causal degree-preserving swaps.
            for j in range(6):
                edges.append({"source": f"{group}-{j}", "target": f"{group}-{j + 6}",
                              "relation": "host", "available_at": si * 1000 + group_number * 100 + j + 5})
    return rows, edges


def separate(rows, edges, confirmation=False):
    selected = [r for r in rows if (r["split"] == "confirmation") == confirmation]
    ids = {r["id"] for r in selected}
    return selected, [e for e in edges if e["target"] in ids]


class EngineGuards(unittest.TestCase):
    def setUp(self):
        self.rows, self.edges = separate(*fixture())

    def test_group_and_future_edge_rejected(self):
        bad = copy.deepcopy(self.rows)
        bad[-1]["group_id"] = bad[0]["group_id"]
        with self.assertRaisesRegex(ValueError, "Group crosses"):
            engine.validate_data(bad, self.edges)
        bad_edges = copy.deepcopy(self.edges)
        bad_edges[0]["available_at"] = 999999
        with self.assertRaisesRegex(ValueError, "unavailable"):
            engine.validate_data(self.rows, bad_edges)
        bad_edges = copy.deepcopy(self.edges)
        bad_edges[0]["source"], bad_edges[0]["target"] = bad_edges[0]["target"], bad_edges[0]["source"]
        with self.assertRaisesRegex(ValueError, "Future"):
            engine.validate_data(self.rows, bad_edges)

    def test_rewire_preserves_relation_degrees_and_causality(self):
        shuffled, receipt = engine.rewire_edges(self.rows, self.edges, 211)
        for endpoint in ("source", "target"):
            self.assertEqual(Counter((e[endpoint], e["relation"]) for e in self.edges),
                             Counter((e[endpoint], e["relation"]) for e in shuffled))
        self.assertGreater(receipt["changed_fraction"], .5)
        by_id = {r["id"]: r for r in self.rows}
        lead_times = lambda edges: Counter((by_id[e["target"]]["group_id"], e["relation"], by_id[e["target"]]["time"] - e["available_at"]) for e in edges)
        self.assertEqual(lead_times(self.edges), lead_times(shuffled))
        engine.validate_data(self.rows, shuffled)

    def test_rewire_edges_arriving_at_distinct_target_times(self):
        by_id = {r["id"]: r for r in self.rows}
        edges = [dict(e, available_at=by_id[e["target"]]["time"]) for e in self.edges]
        shuffled, receipt = engine.rewire_edges(self.rows, edges, 211)
        self.assertGreater(receipt["changed_fraction"], .5)
        self.assertTrue(all(e["available_at"] == by_id[e["target"]]["time"] for e in shuffled))
        engine.validate_data(self.rows, shuffled)

    def test_scaler_and_quality_do_not_use_evaluation_labels(self):
        base = engine.fit_scaler(self.rows)
        mutated = copy.deepcopy(self.rows)
        for r in mutated:
            r["label"] = 999
            if r["split"] != "train":
                r["features"] = [1e9, -1e9]
        self.assertEqual(base, engine.fit_scaler(mutated))
        self.assertEqual(engine.quality_features(self.rows, self.edges, self.edges),
                         engine.quality_features(mutated, self.edges, self.edges))

    def test_gate_allowlist_and_label_invariance(self):
        records = [{"quality": [.2, 2., 0., .5], "label": 0, "mlp_probabilities": [.8, .2]}]
        policy = {"static": {"kind": "degree_threshold", "minimum_observed_in_degree": 1}}
        first = engine.route(records, policy, "static")
        records[0]["label"] = 999
        records[0]["quality"][0] = 999
        self.assertEqual(first, engine.route(records, policy, "static"))
        with self.assertRaisesRegex(ValueError, "Unobservable"):
            engine.policy_inputs(records, (0,))
        with self.assertRaisesRegex(ValueError, "gate_train"):
            engine._fit_policies([{"split": "development"}], [0, 1])

    def test_arrival_delay_removes_unavailable_edges(self):
        delayed = engine.degrade_edges(self.rows, self.edges, {"kind": "arrival_delay", "fraction": 1, "seconds": 100}, 1)
        self.assertEqual(delayed, [])
        self.assertEqual(len(engine.degrade_edges(self.rows, self.edges, {"kind": "clean"}, 1)), len(self.edges))

    def test_alert_threshold_ties_and_calibration_only(self):
        rows = [{"split": "calibration", "scenario": "clean", "seed": 1, "label": 0, "probabilities": [.4, .6]} for _ in range(3)]
        config = {"observation_days": {"calibration": 1}, "alert_budget_per_day": 1}
        threshold = engine._calibrate_alerts(rows, config, [0, 1])["thresholds"]["1"]
        self.assertGreater(threshold, .6)
        rows[0]["split"] = "development"
        with self.assertRaisesRegex(ValueError, "calibration"):
            engine._calibrate_alerts(rows, config, [0, 1])

    def test_paired_bootstrap_preserves_denominators(self):
        rows = []
        for seed in (1, 2):
            for group in ("a", "b"):
                for label in (0, 1):
                    for arm in ("real", "control"):
                        prediction = label if arm == "real" else 0
                        rows.append({"id": f"{group}-{label}", "group_id": group, "seed": seed,
                                     "arm": arm, "label": label, "probabilities": [int(prediction == 0), int(prediction == 1)]})
        result = engine.paired_intervals(rows, "real", "control", [0, 1], 10)
        self.assertAlmostEqual(result["delta_macro_f1"], 2 / 3)
        self.assertEqual(result["independent_groups"], 2)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            engine.paired_intervals(rows + rows[:1], "real", "control", [0, 1], 10)


class EngineIntegration(unittest.TestCase):
    def test_full_synthetic_frozen_pipeline_and_negative_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows, edges = fixture()
            for name, confirmation in (("development", False), ("confirmation", True)):
                subset, links = separate(rows, edges, confirmation)
                engine.write_jsonl(root / f"{name}_rows.jsonl", subset)
                engine.write_jsonl(root / f"{name}_edges.jsonl", links)
            config = {"seeds": [1, 2], "epochs": 2, "hidden_dim": 4,
                      "include_labels": [0, 1], "bootstrap_replicates": 5,
                      "scenarios": [{"name": "clean", "kind": "clean"}, {"name": "drop_half", "kind": "edge_drop", "fraction": .5}]}
            rp, ep = root / "development_rows.jsonl", root / "development_edges.jsonl"
            e1 = engine.run_e1(config, rp, ep, root / "e1", smoke=True)
            self.assertEqual(e1["status"], "SMOKE_NOT_EVIDENCE")
            self.assertFalse(e1["confirmation_revealed"])
            engine.run_e2(config, root / "e1", rp, ep, root / "e2", smoke=True)
            with self.assertRaisesRegex(ValueError, "config differs"):
                engine.run_e3(dict(config, epochs=3), root / "e2", root / "bad", smoke=True)
            engine.run_e3(config, root / "e2", root / "e3", smoke=True)
            policy = root / "e3" / "POLICY_FREEZE.json"
            before = engine.sha256(policy)
            e4 = engine.run_e4(config, root / "e1", policy, root / "confirmation_rows.jsonl", root / "confirmation_edges.jsonl", root / "e4", smoke=True)
            self.assertEqual(before, engine.sha256(policy))
            self.assertFalse(e4["refitted"])
            self.assertEqual(e4["status"], "SMOKE_NOT_EVIDENCE")
            for stage in ("e1", "e2", "e3"):
                self.assertFalse(any(r["split"] == "confirmation" for r in engine.read_jsonl(root / stage / "predictions.jsonl")))
            # Confirmation cannot be smuggled into development under smoke mode.
            engine.write_jsonl(root / "all_rows.jsonl", rows)
            engine.write_jsonl(root / "all_edges.jsonl", edges)
            with self.assertRaisesRegex(ValueError, "separate sealed"):
                engine.run_e1(config, root / "all_rows.jsonl", root / "all_edges.jsonl", root / "bad2", smoke=True)
            # Freeze binds checkpoint bytes, not just filename.
            checkpoint = root / "e1" / e1["costs"][0]["checkpoint"]
            checkpoint.write_bytes(checkpoint.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "checkpoint hash"):
                engine.run_e2(config, root / "e1", rp, ep, root / "bad3", smoke=True)


if __name__ == "__main__":
    unittest.main()
