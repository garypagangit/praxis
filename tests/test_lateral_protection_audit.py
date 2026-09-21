"""Independent arithmetic and tamper checks; no classifier fits or inference."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.apt_benchmark.lateral_protection_experiment import audit


def raises(exception, *, match):
    return unittest.TestCase().assertRaisesRegex(exception, match)


def test_frontier_matches_literal_strict_ties_and_endpoints():
    y = np.array([0, 1, 0, 1, 2, 0, 1])
    scores = np.array([0, 0, .4, .4, .4, 1, 1])
    points = audit.selection_options(scores, y, 0, 1)
    assert [p[0] for p in points] == [-1, 0, .4, 1]
    for threshold, fp, tp, n, l in points:
        flags = scores > threshold
        assert fp == sum(flags[y == 0])
        assert tp == sum(flags[y == 1])
        assert (n, l) == (3, 3)
    assert points[1][1:3] == (2, 2)  # Zero scores are cleared together.
    assert points[-1][1:3] == (0, 0)


def _selection_fixture():
    # Reference captures all 100 lateral rows at 1% FPR. Its own higher cutoff
    # captures 98 at zero FPR. A different detector captures 99 at zero FPR.
    y = np.r_[np.zeros(1000, dtype=int), np.ones(100, dtype=int)]
    reference = np.r_[np.full(990, .1), np.full(10, .8), np.full(98, .9), np.full(2, .7)]
    alternative = np.r_[np.full(1000, .1), np.full(99, .9), .05]
    return y, [{"cell_id": "a", "scores": reference}, {"cell_id": "b", "scores": alternative}]


def test_reference_candidate_and_same_score_ablation_are_independent():
    y, cells = _selection_fixture()
    result = audit.independent_selection(cells, y, 0, 1)
    assert result["choices"]["reference"]["cell_id"] == "a"
    assert result["choices"]["reference"]["selection_lateral_tp"] == 100
    assert result["choices"]["candidate"]["cell_id"] == "b"
    assert result["choices"]["candidate"]["selection_lateral_tp"] == 99
    assert result["choices"]["threshold_only"]["cell_id"] == "a"
    assert result["choices"]["threshold_only"]["selection_lateral_tp"] == 98
    assert not result["candidate_equals_threshold_only"]
    assert not result["candidate_uses_reference_detector"]


def test_changed_threshold_or_eligibility_count_is_rejected():
    y, cells = _selection_fixture()
    expected = audit.independent_selection(cells, y, 0, 1)
    for field, value in [("threshold", .1000001), ("selection_lateral_tp", 100)]:
        bad = copy.deepcopy(expected)
        bad["choices"]["candidate"][field] = value
        with raises(ValueError, match="mismatch"):
            audit.compare(expected, bad)


def test_no_policy_can_split_a_large_tied_normal_attack_score_group():
    y = np.r_[np.zeros(1000, dtype=int), np.ones(100, dtype=int)]
    scores = np.ones(len(y)) * .5
    result = audit.independent_selection([{"cell_id": "a", "scores": scores}], y, 0, 1)
    assert result["status"] == "INFEASIBLE"
    assert result["choices"] == {}


def test_metric_tampering_changes_counts_and_fails_comparison():
    y = np.array([0, 0, 1, 1, 2])
    scores = np.array([.8, .1, .9, .3, .7])
    actual = audit.metrics(y, scores, scores > .5, ["normal", "lateral", "other"], 0)
    assert (actual["tn"], actual["fp"], actual["fn"], actual["tp"]) == (1, 1, 1, 2)
    assert actual["per_stage"]["lateral"]["recall"] == .5
    bad = copy.deepcopy(actual)
    bad["fp"] = 0
    with raises(ValueError, match="mismatch"):
        audit.compare(actual, bad)


def test_infeasible_and_missing_seed_never_become_promising():
    assert audit.independent_gate([], 10)["status"] == "INCOMPLETE"
    records = [{"selection_status": "INFEASIBLE"} for _ in range(10)]
    assert audit.independent_gate(records, 10)["status"] == "INFEASIBLE"


def test_mean_gate_and_summary_tampering():
    def metric(fpr, recall):
        return {"benign_fpr": fpr, "fp": round(fpr * 1000), "benign_n": 1000,
                "per_stage": {"LateralMovement": {"recall": recall, "detected": round(recall * 100), "n": 100}}}
    rows = [{"selection_status": "SELECTED", "partitions": {"verification": {
        "candidate": metric(.005, .94), "reference": metric(.01, .96)}}} for _ in range(10)]
    result = audit.independent_gate(rows, 10)
    assert result["status"] == "DEVELOPMENT_PROMISING"
    assert result["relative_fpr_reduction"] == .5
    bad = copy.deepcopy(result)
    bad["guards"]["lateral_loss_less_than_3pp"] = False
    with raises(ValueError, match="mismatch"):
        audit.compare(result, bad)
    # No false alerts in either policy cannot establish a strict reduction.
    for row in rows:
        row["partitions"]["verification"]["candidate"]["benign_fpr"] = 0
        row["partitions"]["verification"]["reference"]["benign_fpr"] = 0
        row["partitions"]["verification"]["candidate"]["fp"] = 0
        row["partitions"]["verification"]["reference"]["fp"] = 0
    assert audit.independent_gate(rows, 10)["status"] == "DEVELOPMENT_NEGATIVE"


def test_class_mass_weights_and_bad_probabilities():
    y = np.array([0] * 12 + [1] * 3 + [2] * 3)
    balanced = audit.weights(y, "balanced", 3, 1)
    assert np.allclose(np.bincount(y, weights=balanced), [6, 6, 6])
    lateral = audit.weights(y, "lateral2", 3, 1)
    assert np.allclose(np.bincount(y, weights=lateral), [4.5, 9, 4.5])
    assert np.isclose(lateral.mean(), 1)
    with raises(ValueError, match="distribution"):
        audit.check_probabilities(np.full((len(y), 3), .4), y, 3)


class _SyntheticClassifier:
    """Fixed lookup solely for saved-artifact tests; no learned model."""
    def fit(self, X, y, sample_weight=None):
        self.classes_ = np.unique(y)
        return self

    def predict_proba(self, X):
        p = np.full((len(X), len(self.classes_)), .01)
        p[np.arange(len(X)), X[:, 0].astype(int)] = 1 - .01 * (len(self.classes_) - 1)
        return p


class SavedArtifactAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experiments.apt_benchmark.lateral_protection_experiment import backend, run, specification
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.out, cls.data_path, cls.protocol_path = root / "run", root / "DATA.npz", root / "protocol.json"
        classes = np.array(["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"])
        y, split = [], []
        for partition in range(3):
            for k in range(6):
                n = (1100 if k == 3 else 64) if partition == 0 else (200 if k == 3 else 20)
                y.extend([k] * n)
                split.extend([partition] * n)
        y, split = np.asarray(y), np.asarray(split)
        X = np.column_stack([y, np.arange(len(y)) % 7, np.full(len(y), np.nan)]).astype(float)
        data = {"X": X, "y": y, "split": split, "classes": classes,
                "feature_names": np.array(["synthetic_class", "synthetic_index", "empty"]),
                "group_sha256": np.array([hashlib.sha256(str(i).encode()).hexdigest() for i in range(len(y))])}
        np.savez_compressed(cls.data_path, **data)
        cls.protocol = specification.design()
        cls.protocol["data_npz_sha256"] = audit.file_hash(cls.data_path)
        manifest = root / "MANIFEST.json"
        manifest.write_text(json.dumps({"data_npz_sha256": cls.protocol["data_npz_sha256"]}), encoding="utf-8")
        cls.protocol["manifest_sha256"] = audit.file_hash(manifest)
        cls.protocol_path.write_text(json.dumps(cls.protocol), encoding="utf-8")
        cls.out.mkdir()
        cls.data = data
        with patch.object(backend, "make_tree", side_effect=lambda *args, **kwargs: _SyntheticClassifier()), contextlib.redirect_stdout(io.StringIO()):
            receipt = run.prepare(data, cls.protocol, cls.protocol_path, cls.out)
            run.run_group(data, cls.protocol, receipt, cls.out, cls.protocol["groups"][0])
            run.summarize(cls.protocol, receipt, cls.out)
        cls.packet = cls.out / "cells/1024/20260921/xgboost/natural/SELECTION.npz"
        cls.fit_receipt = cls.packet.with_name("FIT_COMPLETE.json")
        cls.fitted = cls.packet.with_name("FITTED.json")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def audit(self):
        return audit.audit_run(self.data_path, self.protocol_path, self.out)

    def test_all_eight_cells_recompute_but_partial_batch_stays_incomplete(self):
        r = self.audit()
        self.assertEqual(r["audit_status"], "PASS")
        self.assertEqual(r["run_status"], "INCOMPLETE")
        self.assertEqual(r["audited_cells"], 8)
        self.assertEqual(len(r["missing_groups"]), 18)

    def test_probability_packet_tamper_is_rejected(self):
        original = self.packet.read_bytes()
        try:
            with np.load(self.packet, allow_pickle=False) as z:
                a = {k: z[k] for k in z.files}
            a["probabilities"][0] = np.roll(a["probabilities"][0], 1)
            np.savez_compressed(self.packet, **a)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.audit()
        finally:
            self.packet.write_bytes(original)

    def test_prefit_partition_tamper_with_rehashed_binding_is_rejected(self):
        path = self.out / "PREFIT_RECEIPT.json"
        original = path.read_bytes()
        try:
            r = audit.read_json(path)
            indices = r["fixed"]["partitions"]["selection"]["indices"]
            indices[0], indices[1] = indices[1], indices[0]
            r["execution_binding"] = audit.value_hash(r["fixed"])
            path.write_text(json.dumps(r), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self.audit()
        finally:
            path.write_bytes(original)

    def test_summary_gate_tamper_is_rejected(self):
        path = self.out / "SUMMARY.json"
        original = path.read_bytes()
        try:
            summary = audit.read_json(path)
            summary["primary_gate"]["status"] = "DEVELOPMENT_PROMISING"
            path.write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self.audit()
        finally:
            path.write_bytes(original)

    def test_weight_tamper_with_refreshed_immediate_hash_is_rejected(self):
        originals = {p: p.read_bytes() for p in [self.fitted, self.fit_receipt]}
        try:
            fitted = audit.read_json(self.fitted)
            fitted["cv_metadata"]["final_training_weights"]["class_weight_sums"][0] += 1
            self.fitted.write_text(json.dumps(fitted), encoding="utf-8")
            fit = audit.read_json(self.fit_receipt)
            fit["files"]["FITTED.json"] = audit.file_hash(self.fitted)
            self.fit_receipt.write_text(json.dumps(fit), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric mismatch"):
                self.audit()
        finally:
            for path, content in originals.items():
                path.write_bytes(content)


class IndependentAuditTests(unittest.TestCase):
    pass


for _name, _function in list(globals().items()):
    if _name.startswith("test_") and callable(_function):
        setattr(IndependentAuditTests, _name, staticmethod(_function))
del _name, _function


if __name__ == "__main__":
    unittest.main()
